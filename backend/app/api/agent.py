import json
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.conversation import Conversation, ConversationMessage
from app.models.academic import Course, Exam
from app.models.announcement import AnnouncementRead, TeacherAnnouncement, TeacherSchedule
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.plan import PlanTask, StudyPlan, TaskStatus
from app.schemas.agent import ChatRequest
from app.services.agent_service import chat, generate_reply
from app.services.llm_service import speech_to_text, _get_client, _get_llm_config, build_system_prompt
from app.services.proactive_engine import evaluate_student

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat")
async def chat_api(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_id = req.conversation_id
    if req.skip_conversation:
        conv_id = None
    elif conv_id:
        conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
        if not conv:
            raise HTTPException(404, "对话不存在")
        db.add(ConversationMessage(conversation_id=conv_id, role="user", content=req.message))
        db.commit()
    else:
        conv = Conversation(user_id=user.id, title="新对话")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    async def generate():
        async for event in chat(req.message, req.history, user, conv_id=conv_id, file_url=req.file_url, deep_think=req.deep_think):
            if isinstance(event, dict):
                if event["type"] == "reasoning":
                    yield f"event: reasoning\ndata: {json.dumps(event['content'], ensure_ascii=False)}\n\n"
                elif event["type"] == "content":
                    yield f"event: content\ndata: {json.dumps(event['content'], ensure_ascii=False)}\n\n"
                elif event["type"] == "meta":
                    # 会话元信息（conversation_id / title / saved）：前端用于即时同步标题与保存状态
                    yield f"event: meta\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            else:
                # 兼容旧的 __SUGGESTIONS__ 格式
                if isinstance(event, str) and event.startswith("__SUGGESTIONS__:"):
                    suggestions_data = event[len("__SUGGESTIONS__:"):]
                    yield f"event: suggestions\ndata: {suggestions_data}\n\n"
                else:
                    yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


class AnalyzeRequest(BaseModel):
    prompt: str


@router.post("/analyze")
async def analyze_api(req: AnalyzeRequest, user: User = Depends(get_current_user)):
    return StreamingResponse(
        generate_reply(req.prompt, user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/speech-to-text")
async def speech_to_text_api(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(400, "文件名为空")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = {"wav", "mp3", "webm", "ogg", "m4a"}
    if ext not in allowed:
        raise HTTPException(400, f"不支持的音频格式: {ext}，支持: {', '.join(allowed)}")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "音频文件不能超过 10MB")
    try:
        text = speech_to_text(content, file.filename)
        return {"text": text}
    except RuntimeError as e:
        raise HTTPException(502, str(e))


# 各角色默认推荐问题（统一 5 条：无历史/取数失败时的兜底）
DEFAULT_RECOMMENDATIONS: dict[UserRole, list[str]] = {
    UserRole.STUDENT: [
        "帮我查一下下周的课程安排",
        "我今天的计划任务有哪些",
        "查一下我的作品集",
        "社区最近有什么热门帖子",
        "有什么好的学习资源推荐",
    ],
    UserRole.TEACHER: [
        "帮我查看今天的待办任务",
        "查一下班级学生的考勤情况",
        "帮我看看最近的校园公告",
        "查询学生的成长记录",
        "帮我看一下学生的心理预警",
    ],
    UserRole.ADMIN: [
        "帮我查看本周的校园公告",
        "查一下平台的用户统计",
        "有什么待处理的系统事项",
        "帮我查一下通知发布情况",
        "最近用户增长情况怎么样",
    ],
}

# 推荐条数：与前端推荐区排版一致
RECOMMEND_COUNT = 5

# 各角色可涵盖的功能范围（用于引导 LLM 生成推荐）
ROLE_FEATURES: dict[UserRole, str] = {
    UserRole.STUDENT: "课表、成绩、请假、通知、考试、成长记录、学习计划、今日任务、打卡、作品集、社区帖子、资源中心、个人画像等",
    UserRole.TEACHER: "待办任务、学生考勤、学生档案、成长记录、校园公告、班级公告、教学日程等",
    UserRole.ADMIN: "校园公告、通知发布、用户管理、数据统计、系统事项等",
}


def _collect_recommend_signals(user: User, db: Session) -> tuple[list[str], list[str]]:
    """从真实数据里取「用户接下来可能关心什么」。

    返回 (画像/待办上下文, 由信号直接得出的候选问题)。
    每一项取数都单独兜底：任何一张表出问题都不该让推荐接口 500。
    """
    context: list[str] = []
    questions: list[str] = []
    today = date.today()

    if user.college:
        context.append(f"学院：{user.college}")
    if user.class_name:
        context.append(f"班级：{user.class_name}")
    if isinstance(user.skills_json, dict):
        interests = user.skills_json.get("interests") or user.skills_json.get("skills") or []
        if isinstance(interests, list) and interests:
            context.append("技能/兴趣：" + "、".join(str(x) for x in interests[:5]))

    if user.role == UserRole.STUDENT:
        # 一周内到期的未完成任务
        try:
            rows = (
                db.query(PlanTask.title, PlanTask.due_date)
                .join(StudyPlan, StudyPlan.id == PlanTask.plan_id)
                .filter(
                    StudyPlan.student_id == user.id,
                    PlanTask.status != TaskStatus.DONE,
                    PlanTask.due_date.isnot(None),
                    PlanTask.due_date <= today + timedelta(days=7),
                )
                .order_by(PlanTask.due_date.asc())
                .limit(3)
                .all()
            )
            if rows:
                context.append("一周内到期的任务：" + "、".join(r[0] for r in rows))
                if any(r[1] and r[1] <= today for r in rows):
                    questions.append("我今天有哪些任务要完成")
                else:
                    questions.append("帮我看看快到期的任务怎么安排")
        except Exception as e:
            logger.warning("推荐信号-计划任务 取数失败: %s", e)

        # 未读校园公告
        try:
            total = db.query(func.count(TeacherAnnouncement.id)).scalar() or 0
            read = (
                db.query(func.count(AnnouncementRead.id))
                .filter(AnnouncementRead.student_id == user.id)
                .scalar()
                or 0
            )
            unread = max(0, total - read)
            if unread:
                context.append(f"未读校园公告：{unread} 条")
                questions.append("最近有什么校园公告")
        except Exception as e:
            logger.warning("推荐信号-公告 取数失败: %s", e)

        # 待审批的请假
        try:
            pending = (
                db.query(func.count(LeaveRequest.id))
                .filter(LeaveRequest.student_id == user.id, LeaveRequest.status == LeaveStatus.PENDING)
                .scalar()
                or 0
            )
            if pending:
                context.append(f"待审批请假：{pending} 条")
                questions.append("我的请假申请批到哪一步了")
        except Exception as e:
            logger.warning("推荐信号-请假 取数失败: %s", e)

        # 今日课程
        try:
            if user.class_group_id:
                courses = (
                    db.query(Course.name, Course.location)
                    .filter(Course.class_group_id == user.class_group_id, Course.day_of_week == today.isoweekday())
                    .order_by(Course.start_period.asc())
                    .limit(4)
                    .all()
                )
                if courses:
                    context.append("今日课程：" + "、".join(c[0] for c in courses))
                    questions.append("我今天有哪些课")
        except Exception as e:
            logger.warning("推荐信号-课表 取数失败: %s", e)

        # 两周内的考试
        try:
            exams = (
                db.query(Exam.course_name, Exam.exam_date)
                .filter(
                    Exam.student_id == user.id,
                    Exam.exam_date >= today,
                    Exam.exam_date <= today + timedelta(days=14),
                )
                .order_by(Exam.exam_date.asc())
                .limit(3)
                .all()
            )
            if exams:
                context.append("近期考试：" + "、".join(f"{e[0]}({e[1]})" for e in exams))
                questions.append("我最近有什么考试要准备")
        except Exception as e:
            logger.warning("推荐信号-考试 取数失败: %s", e)
    else:
        # 教师/管理员：今日日程、待审批请假、近期发布的公告
        try:
            schedules = (
                db.query(TeacherSchedule.content)
                .filter(
                    TeacherSchedule.teacher_id == user.id,
                    TeacherSchedule.date == today,
                    TeacherSchedule.completed.is_(False),
                )
                .limit(3)
                .all()
            )
            if schedules:
                context.append("今日待办日程：" + "、".join(s[0] for s in schedules))
                questions.append("帮我查看今天的待办任务")
        except Exception as e:
            logger.warning("推荐信号-教师日程 取数失败: %s", e)

        try:
            pending = (
                db.query(func.count(LeaveRequest.id))
                .filter(LeaveRequest.tutor_id == user.id, LeaveRequest.status == LeaveStatus.PENDING)
                .scalar()
                or 0
            )
            if pending:
                context.append(f"名下待审批请假：{pending} 条")
                questions.append("有哪些学生请假待我审批")
        except Exception as e:
            logger.warning("推荐信号-教师请假 取数失败: %s", e)

        try:
            mine = (
                db.query(func.count(TeacherAnnouncement.id))
                .filter(TeacherAnnouncement.teacher_id == user.id)
                .scalar()
                or 0
            )
            if mine:
                context.append(f"我发布过的公告：{mine} 条")
        except Exception as e:
            logger.warning("推荐信号-教师公告 取数失败: %s", e)

    return context, questions


async def _generate_recommendations_by_llm(
    user: User, history_text: str, context: list[str]
) -> list[str]:
    """有历史对话时，让 LLM 结合画像/信号/历史生成推荐。失败返回空列表。"""
    role_label = "学生" if user.role == UserRole.STUDENT else "教师" if user.role == UserRole.TEACHER else "管理员"
    context_text = "\n".join(context) if context else "（暂无）"
    prompt = f"""根据以下用户的信息与历史对话，生成{RECOMMEND_COUNT}个用户可能接下来想问的推荐问题。

用户角色：{role_label}

用户当前画像与待办（真实数据，优先结合这些）：
{context_text}

要求：
1. 问题控制在20字以内，自然口语化
2. 结合用户的历史兴趣、画像与待办事项，避免空泛
3. 推荐内容必须贴合该用户角色，涵盖其常用功能（{ROLE_FEATURES.get(user.role, ROLE_FEATURES[UserRole.STUDENT])}），不要推荐其他角色的功能（例如不要给学生推荐班级管理，不要给教师推荐成绩单查询）
4. 直接返回{RECOMMEND_COUNT}个问题的JSON数组，不要其他文字

历史对话记录：
{history_text}

返回格式示例：
["帮我查一下下周的课程安排", "我想看看这学期的成绩单", "最近有什么校园活动通知", "帮我记录一下获奖信息", "我这周的任务完成得怎么样"]"""

    try:
        config = _get_llm_config()
        client = _get_client()
        response = await client.chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=300,
        )
        content = response.choices[0].message.content or ""
        import re
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if not match:
            return []
        items = json.loads(match.group())
        return [str(q).strip() for q in items if isinstance(q, str) and str(q).strip()]
    except Exception as e:
        logger.error("生成推荐失败: %s", e)
        return []


@router.get("/recommendations")
async def get_recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """根据用户角色、画像与真实待办生成推荐问题（统一返回 5 条）。

    无历史对话时直接用信号+默认兜底，不再等一次 LLM（首屏秒开）；
    有历史对话时由 LLM 生成，并用信号/默认补齐到 5 条。
    """
    default_recommendations = DEFAULT_RECOMMENDATIONS.get(
        user.role, DEFAULT_RECOMMENDATIONS[UserRole.STUDENT]
    )[:RECOMMEND_COUNT]
    context, signal_questions = _collect_recommend_signals(user, db)

    # 用户最近的对话消息
    recent_messages = (
        db.query(ConversationMessage)
        .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
        .filter(Conversation.user_id == user.id)
        .order_by(ConversationMessage.timestamp.desc())
        .limit(20)
        .all()
    )

    history_text = ""
    for msg in reversed(recent_messages):
        role = "用户" if msg.role == "user" else "助手"
        history_text += f"{role}: {msg.content[:200]}\n"

    candidates: list[str] = []
    if history_text.strip():
        candidates.extend(await _generate_recommendations_by_llm(user, history_text, context))
    # 信号问题与默认问题用于补位（LLM 少给、或没有历史时）
    candidates.extend(signal_questions)
    candidates.extend(default_recommendations)

    merged: list[str] = []
    for q in candidates:
        q = (q or "").strip()
        if q and q not in merged:
            merged.append(q)
        if len(merged) >= RECOMMEND_COUNT:
            break
    return {"recommendations": merged}


@router.get("/proactive")
async def get_proactive_actions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI 主动发现驾驶舱接口（v3.0 实施文档 §4/§6）

    学生：返回自己的主动触达动作（成长里程碑、久未互动关怀等）
    教师/管理员：返回所带/全体学生的预警与学业关注动作（危机升级、成绩下滑）
    """
    from datetime import datetime, timezone

    actions = []
    if user.role == UserRole.STUDENT:
        actions = [a for a in evaluate_student(db, user) if a.target_role == "student"]
    elif user.role in (UserRole.TEACHER, UserRole.ADMIN):
        students = db.query(User).filter(User.role == UserRole.STUDENT)
        if user.role == UserRole.TEACHER:
            students = students.filter(User.tutor_id == user.id)
        for student in students.all():
            actions.extend(a for a in evaluate_student(db, student) if a.target_role == "teacher")
        actions.sort(key=lambda a: a.priority, reverse=True)

    return {
        "actions": actions[:10],
        "count": len(actions),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "trace_id": f"prc-{user.id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
    }

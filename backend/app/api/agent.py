import asyncio
import json
import logging
import time
from datetime import date, timedelta
from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings
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
from app.services.prompts import build_recommend_questions_prompt
from app.services.proactive_engine import evaluate_student
from app.services.proactive_insight import generate_insight, get_cached_insight
from app.services.daily_report import build_daily_report
from app.services.teacher_daily_report import build_teacher_daily_report
from app.utils.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])

# 各高成本接口限流阈值（用户级，另叠加 IP 兜底）
RATE_CHAT_PER_MIN = 30
RATE_ANALYZE_PER_MIN = 20
RATE_RECOMMENDATIONS_PER_MIN = 10
RATE_STT_PER_MIN = 10


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/chat")
async def chat_api(
    req: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_rate_limit(f"agent:chat:user:{user.id}", RATE_CHAT_PER_MIN, 60, "请求过于频繁，请稍候再试")
    check_rate_limit(f"agent:chat:ip:{_client_ip(request)}", RATE_CHAT_PER_MIN * 3, 60, "当前网络请求过于频繁，请稍候再试")
    if len(req.message) > settings.LLM_MAX_INPUT_CHARS:
        raise HTTPException(400, f"消息过长，最多允许 {settings.LLM_MAX_INPUT_CHARS} 字")
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
        async for event in chat(req.message, req.history, user, conv_id=conv_id, file_url=req.file_url, deep_think=req.deep_think, answer_mode=req.answer_mode):
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
                    # 纯文本兜底（如 agent_service 的异常文案）：必须补 SSE 帧，
                    # 裸写前端解析不到，会表现为「空回复 + 输入中动画一直转」
                    yield "event: content\ndata: " + json.dumps(str(event), ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


class AnalyzeRequest(BaseModel):
    prompt: str


@router.post("/analyze")
async def analyze_api(
    req: AnalyzeRequest,
    request: Request,
    user: User = Depends(get_current_user),
):
    check_rate_limit(f"agent:analyze:user:{user.id}", RATE_ANALYZE_PER_MIN, 60, "请求过于频繁，请稍候再试")
    check_rate_limit(f"agent:analyze:ip:{_client_ip(request)}", RATE_ANALYZE_PER_MIN * 3, 60, "当前网络请求过于频繁，请稍候再试")
    return StreamingResponse(
        generate_reply(req.prompt, user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/speech-to-text")
async def speech_to_text_api(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    check_rate_limit(f"agent:stt:user:{user.id}", RATE_STT_PER_MIN, 60, "语音识别请求过于频繁，请稍候再试")
    check_rate_limit(f"agent:stt:ip:{_client_ip(request)}", RATE_STT_PER_MIN * 3, 60, "当前网络请求过于频繁，请稍候再试")
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


# 各角色默认推荐问题（统一 4 条：无历史/取数失败时的兜底）
DEFAULT_RECOMMENDATIONS: dict[UserRole, list[str]] = {
    UserRole.STUDENT: [
        "帮我查一下下周的课程安排",
        "我今天的计划任务有哪些",
        "查一下我的作品集",
        "社区最近有什么热门帖子",
    ],
    UserRole.TEACHER: [
        "帮我查看今天的待办任务",
        "查一下班级学生的考勤情况",
        "帮我看看最近的校园公告",
        "查询学生的成长记录",
    ],
    UserRole.ADMIN: [
        "帮我查看本周的校园公告",
        "查一下平台的用户统计",
        "有什么待处理的系统事项",
        "帮我查一下通知发布情况",
    ],
}

# 推荐条数：与前端推荐区排版一致（固定 4 条，给矮屏留出欢迎语空间）
RECOMMEND_COUNT = 4

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


# ==================== 推荐缓存 / 后台生成 ====================
# 首屏不能等 LLM：一次生成 1~10s，用户感知就是「为你推荐很久才出来」。
# 策略：响应只走「信号 + 默认」的本地计算（毫秒级），个性化 LLM 结果放后台算，
# 算完写回缓存给下一次请求用；同一用户 5 分钟内直接命中缓存。
_RECO_CACHE_TTL_SECONDS = 300
_RECO_LLM_TIMEOUT_SECONDS = 8.0
_reco_cache: dict = {}


def _reco_cache_get(user_id: int, role: UserRole):
    entry = _reco_cache.get((user_id, role))
    if not entry:
        return None
    if time.time() - entry[0] > _RECO_CACHE_TTL_SECONDS:
        _reco_cache.pop((user_id, role), None)
        return None
    return list(entry[1])


def _reco_cache_set(user_id: int, role: UserRole, items: list) -> None:
    if items:
        _reco_cache[(user_id, role)] = (time.time(), list(items))
        # 缓存别无限长：只保留最近 2000 个用户，避免长期运行内存缓慢上涨
        if len(_reco_cache) > 2000:
            for key in list(_reco_cache.keys())[:500]:
                _reco_cache.pop(key, None)


def _merge_recommendations(*groups) -> list:
    merged: list = []
    for group in groups:
        for q in group or []:
            q = (q or '').strip()
            if q and q not in merged:
                merged.append(q)
            if len(merged) >= RECOMMEND_COUNT:
                return merged
    return merged


async def _refresh_recommendations_in_background(
    user_id: int, role: UserRole, history_text: str, context: list
) -> None:
    """响应之后再让 LLM 生成个性化推荐，写回缓存给下一次用。"""
    try:
        generated = await asyncio.wait_for(
            _generate_recommendations_by_llm(
                SimpleNamespace(role=role), history_text, context
            ),
            timeout=_RECO_LLM_TIMEOUT_SECONDS,
        )
    except Exception as e:
        logger.warning("后台生成推荐失败/超时: %s", e)
        return
    defaults = DEFAULT_RECOMMENDATIONS.get(role, DEFAULT_RECOMMENDATIONS[UserRole.STUDENT])
    merged = _merge_recommendations(generated, defaults)
    _reco_cache_set(user_id, role, merged)


async def _generate_recommendations_by_llm(
    user: User, history_text: str, context: list[str]
) -> list[str]:
    """有历史对话时，让 LLM 结合画像/信号/历史生成推荐。失败返回空列表。"""
    role_label = "学生" if user.role == UserRole.STUDENT else "教师" if user.role == UserRole.TEACHER else "管理员"
    context_text = "\n".join(context) if context else "（暂无）"
    prompt = build_recommend_questions_prompt(
        role_label=role_label,
        context_text=context_text,
        history_text=history_text,
        count=RECOMMEND_COUNT,
        features=ROLE_FEATURES.get(user.role, ROLE_FEATURES[UserRole.STUDENT]),
    )

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
async def get_recommendations(
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据用户角色、画像与真实待办生成推荐问题（固定返回 RECOMMEND_COUNT 条）。

    首屏必须秒回：LLM 生成动辄 1~10s，放在响应路径里就是「打开 App 后为你推荐很久才出来」。
    所以：
      1. 命中缓存（同一用户 5 分钟内）直接返回；
      2. 未命中先用「信号 + 默认」的本地计算立刻返回（毫秒级）；
      3. 有历史对话时，把 LLM 个性化生成丢到后台任务，算完写回缓存，
         下一次请求（重新进页面 / 再开 App）拿到个性化结果。"""
    check_rate_limit(f"agent:rec:user:{user.id}", RATE_RECOMMENDATIONS_PER_MIN, 60, "请求过于频繁，请稍候再试")

    cached = _reco_cache_get(user.id, user.role)
    if cached:
        return {"recommendations": cached}

    default_recommendations = DEFAULT_RECOMMENDATIONS.get(
        user.role, DEFAULT_RECOMMENDATIONS[UserRole.STUDENT]
    )[:RECOMMEND_COUNT]
    context, signal_questions = _collect_recommend_signals(user, db)

    # 最近对话只用于个性化：不在响应路径上等 LLM
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
        history_text += role + ": " + msg.content[:200] + chr(10)

    if history_text.strip():
        background_tasks.add_task(
            _refresh_recommendations_in_background, user.id, user.role, history_text, context
        )

    merged = _merge_recommendations(signal_questions, default_recommendations)
    _reco_cache_set(user.id, user.role, merged)
    return {"recommendations": merged}


@router.get("/proactive")
async def get_proactive_actions(
    student_id: int | None = Query(None, description="按学生过滤，闭环用"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 主动发现驾驶舱接口（v3.0 实施文档 §4/§6）

    学生：返回自己的主动触达动作（今日课程/临考提醒/成绩关注/待办逾期/请假结果/成长里程碑等）
    教师/管理员：返回所带/全体学生的预警与学业关注动作（危机升级、成绩下滑）

    动作来自真实业务信号（课表/考试/成绩/待办/成长档案/请假/对话活跃度），
    不再依赖只有管理员手动刷新才生成的画像快照；本接口只回规则文案以保证首屏速度，
    LLM 个性化洞察由 /proactive/insight 异步补充（命中 30 分钟缓存时这里直接附带）。
    """
    from datetime import datetime, timezone

    actions = []
    if user.role == UserRole.STUDENT:
        # 先按受众过滤再截断：避免教师级动作挤占学生可见名额
        actions = evaluate_student(db, user, target_role="student")
    elif user.role in (UserRole.TEACHER, UserRole.ADMIN):
        students = db.query(User).filter(User.role == UserRole.STUDENT)
        if user.role == UserRole.TEACHER:
            students = students.filter(User.tutor_id == user.id)
        if student_id is not None:
            students = students.filter(User.id == student_id)
        for student in students.all():
            actions.extend(evaluate_student(db, student, target_role="teacher"))
        actions.sort(key=lambda a: a.priority, reverse=True)

    insight = get_cached_insight(user, actions) if (user.role == UserRole.STUDENT and actions) else None

    return {
        "actions": actions[:10],
        "count": len(actions),
        "insight": insight,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "trace_id": f"prc-{user.id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
    }


@router.get("/proactive/insight")
async def get_proactive_insight(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """学生端 AI 洞察（LLM）：卡片先用规则文案渲染，本接口在后台补一句个性化提醒。

    服务端按「学生 + 动作指纹」缓存 30 分钟；未配置 LLM / 超时 / 异常一律返回 null，
    前端保持规则文案即可（不阻塞、不报错）。
    """
    if user.role != UserRole.STUDENT:
        return {"insight": None, "cached": False}

    actions = evaluate_student(db, user, target_role="student")
    if not actions:
        return {"insight": None, "cached": False}

    cached = get_cached_insight(user, actions)
    if cached:
        return {"insight": cached, "cached": True}

    insight = await generate_insight(user, actions)
    return {"insight": insight, "cached": False}


@router.get("/daily-report")
async def get_daily_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI 今日报告：心情（今日优先，缺省沿用昨晚）+ 今日/遗留任务 + 已实现积累 + 实时天气。

    报告含运势、四段带标注的正文，以及可一键加入学习计划的建议。
    天气/LLM 不可用时自动降级，接口始终返回可渲染的内容。
    """
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="今日报告仅学生可用")
    return await build_daily_report(db, user)


@router.get("/teacher-daily-report")
async def get_teacher_daily_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """教师 AI 日报：昨日复盘 + 今日梳理 + 学生成长关注 + 明日规划 + 今日运势。

    事实全部由服务端按教师名下数据计算，LLM 仅负责措辞与重点标注；
    LLM 不可用时自动降级为规则文案，接口始终返回可渲染的内容。
    刷新会带 ``?refresh=1`` 绕过前端缓存，服务端 10 分钟内的事实相同即复用。
    """
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="教师日报仅教师可用")
    return await build_teacher_daily_report(db, user)

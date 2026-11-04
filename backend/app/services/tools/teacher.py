"""教师端工具 handlers：名下学生请假审批、学生查询、危机预警、成长统计、请假分析、待办任务与侧写记录。"""

import logging
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.crisis import AIDialogSummary
from app.models.growth import GrowthRecord
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.teacher_task import TaskSourceType
from app.models.user import User, UserRole
from app.utils.enum_helpers import safe_enum_str, safe_enum_val

logger = logging.getLogger(__name__)




def _get_student_ids_for_teacher(db: Session, user: User) -> list[int]:
    """获取教师名下的学生ID列表"""
    return [s.id for s in db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == user.id).all()]


def _query_pending_leaves(db: Session, args: dict, user: User) -> dict:
    student_ids = _get_student_ids_for_teacher(db, user)
    if not student_ids:
        return {"message": "你暂无名下学生", "leaves": []}
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.student_id.in_(student_ids),
        LeaveRequest.status == LeaveStatus.PENDING,
    ).order_by(LeaveRequest.created_at.desc()).all()
    if not leaves:
        return {"message": "暂无待审批请假", "leaves": []}
    result = []
    for l in leaves:
        student = db.query(User).filter(User.id == l.student_id).first()
        type_names = {"competition": "比赛", "sick": "病假", "personal": "事假", "other": "其他"}
        result.append({
            "id": l.id,
            "student_name": student.name if student else "未知",
            "student_id": l.student_id,
            "start_date": str(l.start_date),
            "end_date": str(l.end_date),
            "reason": l.reason,
            "leave_type": type_names.get(safe_enum_str(l.leave_type, str(l.leave_type)), str(l.leave_type)),
            "created_at": l.created_at.strftime("%m-%d %H:%M") if l.created_at else "",
        })
    return {"message": f"共{len(result)}条待审批请假", "leaves": result}


def _query_students(db: Session, args: dict, user: User) -> dict:
    query = db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == user.id)
    search = args.get("search")
    if search:
        from app.services.knowledge_service import _escape_like
        safe = _escape_like(search)
        like = f"%{safe}%"
        query = query.filter(or_(User.name.like(like, escape="\\"), User.username.like(like, escape="\\"), User.college.like(like, escape="\\")))
    students = query.all()
    if not students:
        return {"message": "暂无名下学生", "students": []}

    student_ids = [s.id for s in students]
    growth_counts = dict(
        db.query(GrowthRecord.student_id, func.count(GrowthRecord.id))
        .filter(GrowthRecord.student_id.in_(student_ids))
        .group_by(GrowthRecord.student_id).all()
    )
    latest_crisis_sub = db.query(
        AIDialogSummary.student_id, AIDialogSummary.level,
        func.row_number().over(
            partition_by=AIDialogSummary.student_id,
            order_by=AIDialogSummary.created_at.desc()
        ).label("rn")
    ).filter(AIDialogSummary.student_id.in_(student_ids)).subquery()
    latest_crises = db.query(latest_crisis_sub).filter(latest_crisis_sub.c.rn == 1).all()
    crisis_map = {c.student_id: c.level for c in latest_crises}

    result = []
    for s in students:
        result.append({
            "id": s.id,
            "name": s.name,
            "username": s.username,
            "college": s.college or "未分配",
            "growth_count": growth_counts.get(s.id, 0),
            "crisis_level": crisis_map.get(s.id),
        })
    return {"message": f"共{len(result)}名学生", "students": result}


def _query_crisis_alerts(db: Session, args: dict, user: User) -> dict:
    student_ids = _get_student_ids_for_teacher(db, user)
    if not student_ids:
        return {"message": "你暂无名下学生", "alerts": []}
    query = db.query(AIDialogSummary).filter(AIDialogSummary.student_id.in_(student_ids))
    resolved = args.get("resolved")
    if resolved is not None:
        query = query.filter(AIDialogSummary.resolved == resolved)
    alerts = query.order_by(AIDialogSummary.created_at.desc()).all()
    if not alerts:
        return {"message": "暂无危机预警", "alerts": []}
    result = []
    for a in alerts:
        student = db.query(User).filter(User.id == a.student_id).first()
        level_names = {"normal": "正常", "mild": "轻度", "moderate": "中度", "severe": "严重"}
        result.append({
            "id": a.id,
            "student_name": student.name if student else "未知",
            "summary": a.summary[:100],
            "level": level_names.get(safe_enum_str(a.level, str(a.level)), str(a.level)),
            "resolved": a.resolved,
            "created_at": a.created_at.strftime("%m-%d %H:%M") if a.created_at else "",
        })
    return {"message": f"共{len(result)}条预警", "alerts": result}


def _resolve_crisis_alert(db: Session, args: dict, user: User) -> dict:
    """处置心理危机预警：只允许操作名下学生，与预警中心同一套字段口径。"""
    try:
        alert_id = int(args.get("alert_id"))
    except (TypeError, ValueError):
        return {"success": False, "message": "缺少有效的预警ID"}
    alert = db.query(AIDialogSummary).filter(AIDialogSummary.id == alert_id).first()
    if not alert:
        return {"success": False, "message": "预警不存在"}
    student = db.query(User).filter(User.id == alert.student_id).first()
    if not student or student.tutor_id != user.id:
        return {"success": False, "message": "无权操作该预警（该学生不在你名下）"}

    resolved = bool(args.get("resolved", True))
    alert.resolved = resolved
    if resolved:
        alert.resolved_by = user.id
        alert.resolved_at = datetime.now(timezone.utc)
    else:
        alert.resolved_by = None
        alert.resolved_at = None
    note = (args.get("note") or "").strip()
    if note:
        alert.intervention_note = note
    db.commit()
    return {
        "success": True,
        "alert_id": alert.id,
        "student_name": student.name,
        "message": f"已将{student.name}的预警标记为{'已处置' if resolved else '待跟进'}",
    }


async def _send_message_to_student(db: Session, args: dict, user: User) -> dict:
    """给名下学生发一对一消息：写入会话，并尽力实时推送（离线不影响落库）。"""
    from app.models.message import Message

    content = (args.get("content") or "").strip()
    if not content:
        return {"success": False, "message": "缺少消息内容"}
    student = _find_my_student(db, user, args.get("student_name"), args.get("student_id"))
    if not student:
        return {"success": False, "message": "未找到该学生（或该学生不在你名下）"}

    msg = Message(sender_id=user.id, receiver_id=student.id, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    try:
        from app.api.messages import manager
        await manager.send_json(student.id, {
            "type": "new_message",
            "id": msg.id,
            "sender_id": user.id,
            "sender_name": user.name,
            "content": content,
            "created_at": msg.created_at.isoformat() if msg.created_at else "",
        })
    except Exception:
        # 学生不在线 / 推送通道异常时消息已入库，打开消息页即可看到
        logger.exception("发送消息后实时推送失败 message_id=%s", msg.id)
    return {
        "success": True,
        "message_id": msg.id,
        "message": f"已给{student.name}发送消息",
    }


def _approve_leave(db: Session, args: dict, user: User) -> dict:
    leave_id = args.get("leave_id")
    action = args.get("action")
    if not leave_id or not action:
        return {"success": False, "message": "缺少必要参数（请假ID和审批操作）"}
    if action not in ("approve", "reject"):
        return {"success": False, "message": "无效操作，必须为 approve 或 reject"}
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        return {"success": False, "message": "请假申请不存在"}
    # 权限检查：只能审批自己名下学生的请假
    student = db.query(User).filter(User.id == leave.student_id).first()
    if not student or student.tutor_id != user.id:
        return {"success": False, "message": "无权审批该请假（该学生不在你名下）"}
    if leave.status != LeaveStatus.PENDING:
        return {"success": False, "message": f"该请假已{leave.status.value}，无法重复审批"}
    if action == "approve":
        leave.status = LeaveStatus.APPROVED
        leave.tutor_id = user.id
        db.commit()
        return {"success": True, "message": f"已批准{student.name}的请假（{leave.start_date}至{leave.end_date}）"}
    elif action == "reject":
        leave.status = LeaveStatus.REJECTED
        leave.tutor_id = user.id
        leave.reject_reason = args.get("reject_reason", "教师驳回")
        db.commit()
        return {"success": True, "message": f"已驳回{student.name}的请假"}
    return {"success": False, "message": "无效操作"}


def _query_student_detail(db: Session, args: dict, user: User) -> dict:
    student_name = args.get("student_name", "")
    student = db.query(User).filter(
        User.name == student_name, User.role == UserRole.STUDENT, User.tutor_id == user.id
    ).first()
    if not student:
        # 模糊搜索
        from app.services.knowledge_service import _escape_like
        safe_name = _escape_like(student_name)
        student = db.query(User).filter(
            User.name.like(f"%{safe_name}%", escape="\\"), User.role == UserRole.STUDENT, User.tutor_id == user.id
        ).first()
    if not student:
        return {"success": False, "message": f"未找到名为'{student_name}'的学生（或该学生不在你名下）"}
    # 成长记录
    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == student.id).order_by(GrowthRecord.date.desc()).all()
    type_names = {"honor": "荣誉", "competition": "竞赛", "practice": "实践", "paper": "论文", "achievement": "成果"}
    growth = [{"title": r.title, "type": type_names.get(safe_enum_str(r.type, str(r.type)), str(r.type)), "date": str(r.date)} for r in records[:5]]
    # 请假
    leaves = db.query(LeaveRequest).filter(LeaveRequest.student_id == student.id).order_by(LeaveRequest.created_at.desc()).all()
    leave_list = [{"start_date": str(l.start_date), "end_date": str(l.end_date), "reason": l.reason, "status": safe_enum_str(l.status, str(l.status))} for l in leaves[:3]]
    # 危机
    crisis = db.query(AIDialogSummary).filter(AIDialogSummary.student_id == student.id).order_by(AIDialogSummary.created_at.desc()).first()
    crisis_info = None
    if crisis:
        level_names = {"normal": "正常", "mild": "轻度", "moderate": "中度", "severe": "严重"}
        crisis_info = {"summary": crisis.summary[:100], "level": level_names.get(safe_enum_str(crisis.level, str(crisis.level)), str(crisis.level)), "resolved": crisis.resolved}
    return {
        "success": True,
        "student": {"name": student.name, "username": student.username, "college": student.college},
        "growth_records": growth,
        "leave_requests": leave_list,
        "crisis_alert": crisis_info,
        "total_records": len(records),
    }


def _query_growth_stats(db: Session, args: dict, user: User) -> dict:
    student_ids = _get_student_ids_for_teacher(db, user)
    if not student_ids:
        return {"message": "你暂无名下学生", "stats": {}}
    stats = db.query(
        GrowthRecord.type, func.count(GrowthRecord.id)
    ).filter(GrowthRecord.student_id.in_(student_ids)).group_by(GrowthRecord.type).all()
    type_names = {"honor": "荣誉", "competition": "竞赛", "practice": "实践", "paper": "论文", "achievement": "成果"}
    result = {type_names.get(safe_enum_str(s[0], str(s[0])), str(s[0])): s[1] for s in stats}
    total = sum(result.values())
    return {"message": f"名下学生共{total}条成长记录", "stats": result, "total": total}


# ============ 数据分析工具 ============

def _analyze_leave(db: Session, args: dict, user: User) -> dict:
    leave_id = args.get("leave_id")
    if not leave_id:
        return {"success": False, "message": "缺少请假ID"}
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        return {"success": False, "message": "请假申请不存在"}
    student = db.query(User).filter(User.id == leave.student_id).first()
    # 权限检查：只能分析自己名下学生的请假（与 _approve_leave 保持一致）
    if user.role != UserRole.ADMIN and (not student or student.tutor_id != user.id):
        return {"success": False, "message": "无权分析该请假（该学生不在你名下）"}
    type_names = {"competition": "比赛", "sick": "病假", "personal": "事假", "other": "其他"}
    return {
        "type": "leave",
        "data": {
            "student": student.name if student else "未知",
            "leave_type": type_names.get(safe_enum_val(leave.leave_type), str(leave.leave_type)),
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "reason": leave.reason,
        },
        "message": f"学生{student.name if student else '未知'}的请假申请：{leave.start_date}至{leave.end_date}，原因：{leave.reason}，请分析是否批准"
    }


# ============ 待办任务 / 侧写记录工具 ============

_TASK_STATUS_TEXT = {
    "pending": "待处理",
    "contacted": "已联系",
    "cared": "已关怀",
    "done": "已完成",
    "expired": "已过期",
}
_RECORD_TYPE_TEXT = {"care": "关怀", "talk": "谈心谈话", "comment": "评语"}


def _find_my_student(
    db: Session,
    user: User,
    student_name: str | None = None,
    student_id: int | None = None,
) -> User | None:
    """按姓名或ID在教师名下学生中定位，避免跨教师越权操作。"""
    base = db.query(User).filter(User.role == UserRole.STUDENT, User.tutor_id == user.id)
    if student_id is not None:
        return base.filter(User.id == student_id).first()
    if student_name:
        from app.services.knowledge_service import _escape_like
        safe = _escape_like(student_name)
        exact = base.filter(User.name == student_name).first()
        if exact:
            return exact
        return base.filter(User.name.like(f"%{safe}%", escape="\\")).first()
    return None


def _query_teacher_tasks(db: Session, args: dict, user: User) -> dict:
    from app.services import teacher_task_service as svc
    tasks, total = svc.list_tasks(
        db,
        user.id,
        status=args.get("status"),
        due=args.get("due"),
        limit=20,
    )
    if not tasks:
        return {"message": "暂无待办任务", "tasks": []}
    return {
        "message": f"共{total}条任务，展示前{len(tasks)}条",
        "tasks": [
            {
                "task_id": t["id"],
                "title": t["title"],
                "student_name": t["student_name"],
                "status": _TASK_STATUS_TEXT.get(t["status"], t["status"]),
                "due_at": str(t["due_at"]) if t["due_at"] else None,
                "overdue": t["overdue"],
            }
            for t in tasks
        ],
    }


def _create_teacher_task(db: Session, args: dict, user: User) -> dict:
    from app.services import teacher_task_service as svc
    title = (args.get("title") or "").strip()
    if not title:
        return {"success": False, "message": "缺少任务标题"}
    wants_student = args.get("student_name") or args.get("student_id")
    student = _find_my_student(db, user, args.get("student_name"), args.get("student_id"))
    if wants_student and not student:
        return {"success": False, "message": "未找到该学生（或该学生不在你名下）"}

    due_at = None
    if args.get("due_at"):
        try:
            due_at = date.fromisoformat(args["due_at"])
        except ValueError:
            return {"success": False, "message": "截止日期格式应为 YYYY-MM-DD"}

    task = svc.create_task(
        db,
        teacher_id=user.id,
        title=title,
        detail=args.get("detail"),
        student_id=student.id if student else None,
        due_at=due_at,
        source_type=TaskSourceType.MANUAL,
    )
    return {
        "success": True,
        "task_id": task.id,
        "message": f"已创建跟进任务：{title}" + (f"（{student.name}）" if student else ""),
    }


_URGENCY_TEXT = {"normal": "普通", "important": "重要", "urgent": "紧急"}


def _query_teacher_schedules(db: Session, args: dict, user: User) -> dict:
    """按月份查询教师日历计划（今日重点/本周计划的数据源）。"""
    from app.models.announcement import TeacherSchedule

    today = date.today()
    try:
        year = int(args.get("year") or today.year)
        month = int(args.get("month") or today.month)
    except (TypeError, ValueError):
        return {"success": False, "message": "年份/月份格式不正确"}
    if not 1 <= month <= 12:
        return {"success": False, "message": "月份应为 1-12"}

    items = db.query(TeacherSchedule).filter(
        TeacherSchedule.teacher_id == user.id,
        func.extract("year", TeacherSchedule.date) == year,
        func.extract("month", TeacherSchedule.date) == month,
    ).order_by(TeacherSchedule.date.asc()).all()
    if not items:
        return {"message": f"{year}年{month}月暂无日程安排", "schedules": []}
    return {
        "message": f"{year}年{month}月共{len(items)}条日程",
        "schedules": [
            {
                "schedule_id": i.id,
                "date": str(i.date),
                "content": i.content,
                "urgency": _URGENCY_TEXT.get(safe_enum_val(i.urgency), safe_enum_val(i.urgency)),
                "completed": bool(i.completed),
                "overdue": (not i.completed) and i.date < today,
            }
            for i in items
        ],
    }


def _create_teacher_schedule(db: Session, args: dict, user: User) -> dict:
    """新增教师日程（与 /api/teacher/schedules 同一张表、同一口径）。"""
    from app.models.announcement import TeacherSchedule, UrgencyLevel

    content = (args.get("content") or "").strip()
    if not content:
        return {"success": False, "message": "缺少日程内容"}
    raw_date = args.get("date")
    if raw_date:
        try:
            day = date.fromisoformat(str(raw_date))
        except ValueError:
            return {"success": False, "message": "日期格式应为 YYYY-MM-DD"}
    else:
        day = date.today()
    urgency = args.get("urgency") if args.get("urgency") in _URGENCY_TEXT else "normal"

    item = TeacherSchedule(
        teacher_id=user.id, date=day, content=content, urgency=UrgencyLevel(urgency),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "success": True,
        "schedule_id": item.id,
        "message": f"已加入日程：{day} {content}（{_URGENCY_TEXT[urgency]}）",
    }


def _publish_class_announcement(db: Session, args: dict, user: User) -> dict:
    """发布班级公告并即时推送站内通知（与公告页发布链路一致）。"""
    from app.models.announcement import TeacherAnnouncement, UrgencyLevel
    from app.models.notification import NotificationType
    from app.services.notification_service import send_batch_notifications

    title = (args.get("title") or "").strip()
    content = (args.get("content") or "").strip()
    if not title or not content:
        return {"success": False, "message": "公告标题和正文都不能为空"}
    urgency = args.get("urgency") if args.get("urgency") in _URGENCY_TEXT else "normal"

    item = TeacherAnnouncement(
        teacher_id=user.id, title=title, content=content, urgency=UrgencyLevel(urgency),
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    student_ids = _get_student_ids_for_teacher(db, user)
    notified = 0
    if student_ids:
        try:
            send_batch_notifications(
                db,
                student_ids,
                title=f"[{_URGENCY_TEXT[urgency]}公告] {title}",
                content=content[:200],
                notification_type=NotificationType.ANNOUNCEMENT,
                link="/student",
                related_id=item.id,
                sender_id=user.id,
                level=UrgencyLevel(urgency),
            )
            notified = len(student_ids)
        except Exception:
            # 公告已发布成功，通知失败不应让整个工具调用报错
            logger.exception("发布班级公告后推送通知失败 announcement_id=%s", item.id)
    return {
        "success": True,
        "announcement_id": item.id,
        "message": f"已发布公告「{title}」" + (
            f"，并通知{notified}名学生" if notified else "（未推送通知：暂无名下学生或推送失败）"
        ),
    }


def _create_care_record(db: Session, args: dict, user: User) -> dict:
    from app.services import care_record_service as svc
    content = (args.get("content") or "").strip()
    if not content:
        return {"success": False, "message": "缺少记录内容"}
    student = _find_my_student(db, user, args.get("student_name"), args.get("student_id"))
    if not student:
        return {"success": False, "message": "未找到该学生（或该学生不在你名下）"}

    record_type = args.get("record_type") or "care"
    if record_type not in _RECORD_TYPE_TEXT:
        return {"success": False, "message": "记录类型仅支持 care/talk/comment"}
    record = svc.create_record(
        db,
        teacher_id=user.id,
        student_id=student.id,
        content=content,
        record_type=record_type,
        is_private=bool(args.get("is_private", True)),
    )
    return {
        "success": True,
        "record_id": record.id,
        "message": f"已为{student.name}记录一条{_RECORD_TYPE_TEXT[record_type]}",
    }


def _query_care_records(db: Session, args: dict, user: User) -> dict:
    from app.services import care_record_service as svc
    student = _find_my_student(db, user, args.get("student_name"), args.get("student_id"))
    if not student:
        return {"success": False, "message": "未找到该学生（或该学生不在你名下）"}
    records, total = svc.list_records(db, student_id=student.id, limit=10)
    if not records:
        return {"message": f"{student.name}暂无侧写记录", "records": []}
    return {
        "message": f"{student.name}共{total}条记录，展示最近{len(records)}条",
        "records": [
            {
                "record_id": r["id"],
                "record_type": _RECORD_TYPE_TEXT.get(r["record_type"], r["record_type"]),
                "content": r["content"][:120],
                "created_at": r["created_at"][:10],
            }
            for r in records
        ],
    }


# ============ P1 模块工具：成长档案 / 问卷互评 / 关怀中心 / 家校沟通 ============


def _query_my_portfolio(db: Session, args: dict, user: User) -> dict:
    from app.services import teacher_portfolio_service as svc
    report = svc.report(db, user.id)
    if not report["total"]:
        return {"message": "你的成长档案还是空的，可以在「成长档案」页沉淀第一条", "by_type": report["by_type"]}
    return {
        "message": f"你共有 {report['total']} 条成长档案",
        "by_type": [t for t in report["by_type"] if t["count"]],
        "recent": [
            {"title": it["title"], "type": it["item_type"], "occurred_on": it["occurred_on"]}
            for it in report["items"][:8]
        ],
    }


def _create_portfolio_item(db: Session, args: dict, user: User) -> dict:
    from app.services import teacher_portfolio_service as svc
    title = (args.get("title") or "").strip()
    if not title:
        return {"success": False, "message": "缺少档案标题"}
    item_type = args.get("item_type") or "case"
    if item_type not in ("case", "honor", "training", "research"):
        return {"success": False, "message": "类型仅支持 case/honor/training/research"}
    occurred_on = None
    if args.get("occurred_on"):
        try:
            occurred_on = date.fromisoformat(args["occurred_on"])
        except ValueError:
            return {"success": False, "message": "日期格式应为 YYYY-MM-DD"}
    item = svc.create_item(
        db,
        teacher_id=user.id,
        title=title,
        item_type=item_type,
        reflection=args.get("reflection"),
        occurred_on=occurred_on,
    )
    label = svc.TYPE_LABELS.get(item_type, item_type)
    return {"success": True, "item_id": item.id, "message": f"已添加一条{label}成长档案：{title}"}


def _query_my_survey_results(db: Session, args: dict, user: User) -> dict:
    from app.services import peer_survey_service as svc
    results = svc.my_results(db, user.id)
    if not results:
        return {"message": "暂无针对你的问卷评价"}
    out = []
    for r in results:
        out.append(
            {
                "title": r["title"],
                "response_count": r["response_count"],
                "enough_sample": r["enough_sample"],
                "overall_average": r["overall_average"],
                "note": "样本不足，暂不展示分布" if not r["enough_sample"] else "",
            }
        )
    return {"message": f"共{len(results)}份问卷有你被评的记录", "results": out}


def _query_care_calendar(db: Session, args: dict, user: User) -> dict:
    from app.services import care_center_service as svc
    events = svc.list_events(db, user.id, args.get("month"))
    if not events:
        return {"message": "本月的关怀日历还是空的，可用自动生成或手动添加", "events": []}
    return {
        "message": f"本月共{len(events)}条关怀事项",
        "events": [
            {
                "event_id": e["id"],
                "event_type": svc.EVENT_TYPE_LABELS.get(e["event_type"], e["event_type"]),
                "date": str(e["event_date"]),
                "title": e["title"],
                "student_name": e["student_name"],
            }
            for e in events
        ],
    }


def _query_guardian_logs(db: Session, args: dict, user: User) -> dict:
    from app.services import guardian_service as svc
    student = _find_my_student(db, user, args.get("student_name"), args.get("student_id"))
    if not student:
        return {"success": False, "message": "未找到该学生（或该学生不在你名下）"}
    logs = svc.list_logs(db, user.id, student_id=student.id, limit=10)
    guardians = svc.list_guardians(db, student.id)
    if not logs and not guardians:
        return {"message": f"{student.name}暂无家长联系人与沟通记录"}
    return {
        "message": f"{student.name}：联系人 {len(guardians)} 位，沟通记录 {len(logs)} 条",
        "guardians": [
            {"name": g["name"], "relation": g["relation"], "phone": g["phone_masked"], "is_primary": g["is_primary"]}
            for g in guardians
        ],
        "logs": [
            {
                "scene": svc.SCENE_LABELS.get(l["scene"], l["scene"]),
                "channel": l["channel"],
                "status": l["status"],
                "content": l["content_summary"][:120],
                "created_at": l["created_at"][:10],
            }
            for l in logs
        ],
    }


# ============ P2 底座工具：学情事件 / AI 学情诊断 / 审批流程 ============


def _query_learning_events(db: Session, args: dict, user: User) -> dict:
    """学情数据底座：按学生聚合学情事件（谓语分布 + 最近时间线）。"""
    from app.services import learning_event_service
    student = _find_my_student(db, user, args.get("student_name"), args.get("student_id"))
    if not student:
        return {"success": False, "message": "未找到该学生（或该学生不在你名下）"}
    days = int(args.get("days") or 30)
    agg = learning_event_service.aggregate(db, student.id, days=days)
    if not agg["total"]:
        return {"message": f"{student.name}近{days}天没有学情事件记录", "by_verb": []}
    return {
        "message": f"{student.name}近{days}天共 {agg['total']} 条学情事件",
        "by_verb": agg["by_verb"][:8],
        "recent": [
            {"verb": e["verb"], "object_type": e["object_type"], "occurred_at": e["occurred_at"][:10]}
            for e in agg["recent"][:8]
        ],
    }


async def _query_student_insight(db: Session, args: dict, user: User) -> dict:
    """AI 学情诊断：可溯源画像 + 辅导建议（LLM 不可用时自动降级为规则建议）。"""
    from app.services import student_insight_service
    student = _find_my_student(db, user, args.get("student_name"), args.get("student_id"))
    if not student:
        return {"success": False, "message": "未找到该学生（或该学生不在你名下）"}
    days = int(args.get("days") or 30)
    insight = await student_insight_service.get_insight(db, student.id, days=days)
    return {
        "message": insight["advice"],
        "risk_level": insight["profile"]["risk_level"],
        "risk_reasons": insight["profile"]["risk_reasons"],
        "evidence": insight["profile"]["evidence"],
        "degraded": insight["degraded"],
    }


def _query_my_workflows(db: Session, args: dict, user: User) -> dict:
    """查看我发起 / 参与的审批流程实例及当前待办节点。"""
    from app.services import workflow_engine
    status = args.get("status")
    instances = workflow_engine.list_instances(
        db, initiator_id=None if args.get("all") else user.id, status=status, limit=20
    )
    if not instances:
        return {"message": "暂无流程实例", "instances": []}
    return {
        "message": f"共{len(instances)}个流程实例",
        "instances": [
            {
                "instance_id": i["id"],
                "def_name": i["def_name"],
                "status": i["status"],
                "current_node": (i.get("current_node") or {}).get("name", ""),
                "biz_type": i["biz_type"],
                "biz_id": i["biz_id"],
            }
            for i in instances
        ],
    }


# ============ 求助受理（学生求助 → 辅导员帮扶闭环）============

_HELP_STATUS_TEXT = {"pending": "待受理", "processing": "帮扶中", "resolved": "已帮助"}


def _query_help_requests(db: Session, args: dict, user: User) -> dict:
    from app.services import help_request_service as svc
    records = svc.list_for_teacher(db, user.id, status=args.get("status"), limit=20)
    if not records:
        return {"message": "暂无学生求助", "requests": []}
    return {
        "message": f"共{len(records)}条学生求助",
        "requests": [
            {
                "request_id": r["id"],
                "student_name": r["student_name"] or "匿名同学",
                "category": svc.CATEGORY_LABELS.get(r["category"], r["category"]),
                "status": _HELP_STATUS_TEXT.get(r["status"], r["status"]),
                "content": r["content"][:80],
                "created_at": r["created_at"][:10],
            }
            for r in records
        ],
    }


def _reply_help_request(db: Session, args: dict, user: User) -> dict:
    from app.services import help_request_service as svc
    request_id = args.get("request_id")
    reply = (args.get("reply") or "").strip()
    if not request_id:
        return {"success": False, "message": "缺少 request_id（求助ID）"}
    if not reply:
        return {"success": False, "message": "请填写回复内容"}
    try:
        record = svc.reply(
            db,
            teacher_id=user.id,
            is_admin=(user.role == UserRole.ADMIN),
            request_id=int(request_id),
            reply=reply,
            status=args.get("status") or "resolved",
        )
    except HTTPException as e:
        return {"success": False, "message": e.detail}
    status_text = _HELP_STATUS_TEXT.get(record.status.value, record.status.value)
    return {
        "success": True,
        "request_id": record.id,
        "status": status_text,
        "message": f"✅ 已回复该求助（状态：{status_text}）",
    }


# ============================================================
# 教学域工具（PH3）：课表/任课教师、出勤、作业、成绩
# 与 teaching_service 共用同一套数据口径，保证 AI 看到的数字与页面一致
# ============================================================

def _my_teaching_courses(db: Session, user: User, semester: str | None = None):
    """我教的课（严格按 Course.teacher_id，不含历史字符串兜底以外的猜测）。"""
    from app.services.teaching_scope import default_semester, my_courses
    sem = semester or default_semester(db)
    return sem, my_courses(db, user, sem)


def _query_my_courses(db: Session, args: dict, user: User) -> dict:
    """我的课表 + 任课教师视图：既回答"我这周有什么课"，也回答"某位老师的课表"。"""
    from app.models.academic import Course
    from app.services.teaching_scope import default_semester

    semester = args.get("semester") or default_semester(db)
    teacher_name = (args.get("teacher_name") or "").strip()
    weekday = args.get("weekday")
    try:
        weekday = int(weekday) if weekday is not None else None
    except (TypeError, ValueError):
        weekday = None

    q = db.query(Course).filter(Course.semester == semester)
    if teacher_name:
        # 按任课教师看课表：姓名匹配（含模糊），不限本人
        from app.services.knowledge_service import _escape_like
        safe = _escape_like(teacher_name)
        q = q.filter(Course.teacher.like(f"%{safe}%", escape="\\"))
    else:
        q = q.filter(Course.teacher_id == user.id)
    if weekday is not None:
        q = q.filter(Course.day_of_week == weekday)

    courses = q.order_by(Course.day_of_week, Course.start_period).all()
    if not courses:
        scope = f"{teacher_name} 老师" if teacher_name else "你"
        return {"message": f"{semester} 学期 {scope} 在该条件下暂无可查课程", "courses": []}

    # 班级名称映射（Course 只存 class_group_id）
    from app.models.academic import ClassGroup
    cls_ids = {c.class_group_id for c in courses if c.class_group_id}
    cls_names = {}
    if cls_ids:
        for g in db.query(ClassGroup).filter(ClassGroup.id.in_(cls_ids)).all():
            cls_names[g.id] = g.name

    week_map = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}
    return {
        "message": f"{semester} 学期共 {len(courses)} 门/次课程",
        "semester": semester,
        "courses": [
            {
                "course_id": c.id,
                "course_name": c.name,
                "teacher": c.teacher,
                "class_name": cls_names.get(c.class_group_id, ""),
                "weekday": week_map.get(c.day_of_week, f"周{c.day_of_week}"),
                "period": f"第{c.start_period}-{c.end_period}节",
                "location": c.location,
                "credit": float(c.credit) if c.credit is not None else None,
            }
            for c in courses
        ],
    }


def _resolve_my_course(db: Session, user: User, course_id=None, course_name=None):
    """把 AI 传入的课程名/ID 解析成"我教的课"，避免越权。"""
    from app.models.academic import Course
    from app.services.knowledge_service import _escape_like
    from app.services.teaching_scope import teacher_course_filter

    base = db.query(Course).filter(teacher_course_filter(user))
    if course_id:
        try:
            cid = int(course_id)
        except (TypeError, ValueError):
            return None
        return base.filter(Course.id == cid).first()
    if course_name:
        exact = base.filter(Course.name == course_name).first()
        if exact:
            return exact
        return base.filter(
            Course.name.like(f"%{_escape_like(course_name)}%", escape="\\")
        ).first()
    return None


def _query_class_attendance(db: Session, args: dict, user: User) -> dict:
    """班级出勤概况：某门课近几次点名的到课率与缺勤名单。"""
    from app.models.academic import ClassGroup
    from app.models.teaching import Attendance, AttendanceStatus

    course = _resolve_my_course(db, user, args.get("course_id"), args.get("course_name"))
    if not course:
        return {"success": False, "message": "未找到该课程，或该课程不在你名下"}

    recs = db.query(Attendance).filter(Attendance.course_id == course.id).order_by(
        Attendance.attend_date.desc(), Attendance.period_start
    ).limit(400).all()
    if not recs:
        # 提前返回也要带全字段，避免 AI 拿到 class_name=None 后误判
        cls0 = db.query(ClassGroup).filter_by(id=course.class_group_id).first() if course.class_group_id else None
        return {
            "success": True,
            "course_name": course.name,
            "class_name": cls0.name if cls0 else "",
            "sessions": 0,
            "records": 0,
            "attendance_rate": None,
            "absent_count": 0,
            "absent_top": [],
            "message": f"《{course.name}》还没有点名记录",
        }

    sessions = {}
    for r in recs:
        key = (r.attend_date, r.period_start)
        sessions.setdefault(key, []).append(r)
    total = len(recs)
    present_like = sum(1 for r in recs if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE, AttendanceStatus.LEAVE))
    absent_like = sum(1 for r in recs if r.status == AttendanceStatus.ABSENT)
    rate = round(present_like / total * 100, 1) if total else 0.0

    # 缺勤最多的学生（按次数倒序，取前 5）
    absent_count: dict[int, int] = {}
    for r in recs:
        if r.status == AttendanceStatus.ABSENT:
            absent_count[r.student_id] = absent_count.get(r.student_id, 0) + 1
    top_ids = sorted(absent_count, key=lambda k: absent_count[k], reverse=True)[:5]
    names = {}
    if top_ids:
        for s in db.query(User).filter(User.id.in_(top_ids)).all():
            names[s.id] = s.name

    cls = db.query(ClassGroup).filter_by(id=course.class_group_id).first() if course.class_group_id else None
    cls_name = cls.name if cls else ""
    return {
        "success": True,
        "course_name": course.name,
        "class_name": cls_name,
        "sessions": len(sessions),
        "records": total,
        "attendance_rate": rate,
        "absent_count": absent_like,
        "absent_top": [
            {"student_name": names.get(sid, "未知"), "absent_times": absent_count[sid]}
            for sid in top_ids
        ],
        "message": f"《{course.name}》累计 {len(sessions)} 次点名，到课率 {rate}%，旷课 {absent_like} 人次",
    }


def _query_homework_status(db: Session, args: dict, user: User) -> dict:
    """作业提交概况：谁交了、谁没交、谁已批改。"""
    from app.models.academic import Course
    from app.models.teaching import Homework, HomeworkSubmission, SubmissionStatus
    from app.services.teaching_scope import teacher_course_filter

    title_kw = (args.get("homework_title") or "").strip()
    course = _resolve_my_course(db, user, args.get("course_id"), args.get("course_name"))

    q = db.query(Homework)
    if course:
        q = q.filter(Homework.course_id == course.id)
    else:
        course_ids = [c.id for c in db.query(Course).filter(teacher_course_filter(user)).all()]
        if not course_ids:
            return {"success": False, "message": "你暂无名下课程"}
        q = q.filter(Homework.course_id.in_(course_ids))
    if title_kw:
        from app.services.knowledge_service import _escape_like
        q = q.filter(Homework.title.like(f"%{_escape_like(title_kw)}%", escape="\\"))

    hw = q.order_by(Homework.created_at.desc()).first()
    if not hw:
        return {"success": False, "message": "未找到符合条件的作业"}

    all_subs = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == hw.id).all()
    submitted = [s for s in all_subs if s.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED, SubmissionStatus.LATE)]
    graded = [s for s in all_subs if s.status == SubmissionStatus.GRADED]
    not_submitted = [s for s in all_subs if s.status == SubmissionStatus.PENDING]
    names = {}
    wait_ids = [s.student_id for s in not_submitted[:10]]
    if wait_ids:
        for s in db.query(User).filter(User.id.in_(wait_ids)).all():
            names[s.id] = s.name

    return {
        "success": True,
        "homework_id": hw.id,
        "title": hw.title,
        "due_at": str(hw.due_at) if hw.due_at else None,
        "total": len(all_subs),
        "submitted": len(submitted),
        "graded": len(graded),
        "not_submitted": len(not_submitted),
        "not_submitted_names": [names.get(s.student_id, "未知") for s in not_submitted[:10]],
        "message": f"《{hw.title}》应交 {len(all_subs)} 人，已交 {len(submitted)} 人，已批改 {len(graded)} 人，未交 {len(not_submitted)} 人",
    }


def _query_class_grade(db: Session, args: dict, user: User) -> dict:
    """班级成绩概况：均分、及格率、不及格名单与分数段分布。"""
    from app.models.academic import Grade

    course = _resolve_my_course(db, user, args.get("course_id"), args.get("course_name"))
    if not course:
        return {"success": False, "message": "未找到该课程，或该课程不在你名下"}

    # Grade 通过「课程名 + 学期」关联课程（无 course_id 外键），必须与 teaching.py 同口径
    grades = db.query(Grade).filter(
        Grade.course_name == course.name,
        Grade.semester == course.semester,
    ).all()
    scores = [float(g.score) for g in grades if g.score is not None]
    if not scores:
        return {"success": True, "message": f"《{course.name}》还没有成绩记录", "course_name": course.name}

    line = float(args.get("pass_line") or 60.0)
    passed = [s for s in scores if s >= line]
    fail_rows = sorted(
        [g for g in grades if g.score is not None and float(g.score) < line],
        key=lambda g: float(g.score),
    )[:10]
    names = {}
    if fail_rows:
        for s in db.query(User).filter(User.id.in_([g.student_id for g in fail_rows])).all():
            names[s.id] = s.name

    buckets = {"0-59": 0, "60-69": 0, "70-79": 0, "80-89": 0, "90-100": 0}
    for sc in scores:
        if sc < 60:
            buckets["0-59"] += 1
        elif sc < 70:
            buckets["60-69"] += 1
        elif sc < 80:
            buckets["70-79"] += 1
        elif sc < 90:
            buckets["80-89"] += 1
        else:
            buckets["90-100"] += 1

    avg = round(sum(scores) / len(scores), 1)
    return {
        "success": True,
        "course_name": course.name,
        "graded_count": len(scores),
        "avg": avg,
        "max": max(scores),
        "min": min(scores),
        "pass_rate": round(len(passed) / len(scores) * 100, 1),
        "distribution": buckets,
        "fail_names": [{"student_name": names.get(g.student_id, "未知"), "score": float(g.score)} for g in fail_rows],
        "message": f"《{course.name}》已录 {len(scores)} 人，均分 {avg}，及格率 {round(len(passed)/len(scores)*100, 1)}%",
    }


def _query_attendance_roster(db: Session, args: dict, user: User) -> dict:
    """某门课某次课的应到名单（供 AI 一键点名前预览）。"""
    from app.models.leave import LeaveRequest, LeaveStatus

    course = _resolve_my_course(db, user, args.get("course_id"), args.get("course_name"))
    if not course:
        return {"success": False, "message": "未找到该课程，或该课程不在你名下"}

    try:
        attend_date = date.fromisoformat(args["attend_date"]) if args.get("attend_date") else date.today()
    except ValueError:
        return {"success": False, "message": "日期格式应为 YYYY-MM-DD"}

    # 课程所属班级学生（与 teaching.py 的 _class_students 同口径：按 class_group_id 精确匹配）
    students = []
    if course.class_group_id:
        students = (
            db.query(User)
            .filter(User.role == UserRole.STUDENT, User.class_group_id == course.class_group_id)
            .order_by(User.name)
            .all()
        )
    if not students:
        return {"success": True, "message": f"《{course.name}》未关联到班级学生", "students": []}

    approved = {
        l.student_id
        for l in db.query(LeaveRequest).filter(
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= attend_date,
            LeaveRequest.end_date >= attend_date,
        ).all()
    }
    return {
        "success": True,
        "course_name": course.name,
        "attend_date": str(attend_date),
        "count": len(students),
        "students": [
            {
                "student_id": s.id,
                "student_name": s.name,
                "on_approved_leave": s.id in approved,
            }
            for s in students
        ],
        "message": f"《{course.name}》{attend_date} 应到 {len(students)} 人，其中 {len(approved & {s.id for s in students})} 人已批假（点名时将自动记为请假而非旷课）",
    }

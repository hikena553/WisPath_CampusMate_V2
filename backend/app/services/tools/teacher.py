"""教师端工具 handlers：名下学生请假审批、学生查询、危机预警、成长统计、请假分析、待办任务与侧写记录。"""

from datetime import date

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.crisis import AIDialogSummary
from app.models.growth import GrowthRecord
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.teacher_task import TaskSourceType
from app.models.user import User, UserRole
from app.utils.enum_helpers import safe_enum_str, safe_enum_val




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

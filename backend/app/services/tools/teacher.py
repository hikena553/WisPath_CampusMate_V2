"""教师端工具 handlers：名下学生请假审批、学生查询、危机预警、成长统计、请假分析。"""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.crisis import AIDialogSummary
from app.models.growth import GrowthRecord
from app.models.leave import LeaveRequest, LeaveStatus
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

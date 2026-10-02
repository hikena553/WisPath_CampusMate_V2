"""学生端工具 handlers：请假、成长档案、办事服务、课表/成绩/考试/知识库/风景/公告查询、学情分析。"""

import httpx

from datetime import date, datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.academic import Course, Exam, Grade
from app.models.campus import CampusScenery
from app.models.conversation import Conversation
from app.models.growth import GrowthRecord, RecordType
from app.models.knowledge import KnowledgeItem
from app.models.leave import LeaveRequest
from app.models.service import ServiceTicket, TicketType
from app.models.user import User
from app.utils.enum_helpers import safe_enum_str




def _create_leave(db: Session, args: dict, user: User) -> dict:
    start_date = args.get("start_date")
    end_date = args.get("end_date")
    reason = args.get("reason")
    missing = []
    if not start_date:
        missing.append("start_date（开始日期）")
    if not end_date:
        missing.append("end_date（结束日期）")
    if not reason:
        missing.append("reason（请假原因）")
    if missing:
        return {"success": False, "message": f"缺少必要参数：{', '.join(missing)}，请补充完整后重试"}

    try:
        start_d = date.fromisoformat(str(start_date)[:10])
        end_d = date.fromisoformat(str(end_date)[:10])
    except ValueError:
        return {"success": False, "message": "日期格式不正确，请使用 YYYY-MM-DD 格式"}
    today = date.today()
    if start_d < today:
        return {"success": False, "message": "开始日期不能早于今天"}
    if end_d < start_d:
        return {"success": False, "message": "结束日期不能早于开始日期"}
    if (end_d - start_d).days > 14:
        return {"success": False, "message": "请假时长不能超过15天"}

    leave = LeaveRequest(
        student_id=user.id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        leave_type=args.get("leave_type", "other"),
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    type_names = {"competition": "比赛", "sick": "病假", "personal": "事假", "other": "其他"}
    return {
        "success": True, "leave_id": leave.id,
        "start_date": str(leave.start_date), "end_date": str(leave.end_date),
        "reason": leave.reason, "leave_type": type_names.get(leave.leave_type, leave.leave_type),
        "status": "pending",
        "message": f"✅ 请假申请已提交！假期：{leave.start_date} 至 {leave.end_date}，原因：{leave.reason}。等待辅导员审批。"
    }


def _create_growth_record(db: Session, args: dict, user: User) -> dict:
    type_names = {"honor": "荣誉", "competition": "竞赛", "practice": "实践", "paper": "论文", "achievement": "成果"}
    record_type_str = args.get("record_type", "honor")
    title = args.get("title", "")
    date = args.get("date", "")
    description = args.get("description", "")
    level = args.get("honor_level") or args.get("competition_level") or ""
    organizer = args.get("organizer", "")
    attachment = args.get("attachment_url", "")

    lines = [f"类型: {type_names.get(record_type_str, record_type_str)}", f"标题: {title}"]
    if date:
        lines.append(f"日期: {date}")
    if description:
        lines.append(f"描述: {description}")
    if level:
        lines.append(f"等级: {level}")
    if organizer:
        lines.append(f"主办方: {organizer}")
    if attachment:
        lines.append(f"附件: {attachment}")

    return {
        "success": True,
        "pending": True,
        "record_type": record_type_str,
        "title": title,
        "date": date,
        "description": description,
        "honor_level": args.get("honor_level"),
        "organizer": organizer,
        "competition_level": args.get("competition_level"),
        "practice_type": args.get("practice_type"),
        "paper_type": args.get("paper_type"),
        "paper_name": args.get("paper_name"),
        "first_author": args.get("first_author"),
        "achievement_type": args.get("achievement_type"),
        "achievement_name": args.get("achievement_name"),
        "attachment_url": attachment,
        "display": "\n".join(lines),
        "message": "以上是从材料中提取的信息，请确认是否正确。确认后我将保存到你的成长档案。"
    }


def _confirm_growth_record(db: Session, args: dict, user: User) -> dict:
    type_map = {"honor": RecordType.HONOR, "competition": RecordType.COMPETITION, "practice": RecordType.PRACTICE, "paper": RecordType.PAPER, "achievement": RecordType.ACHIEVEMENT}
    type_names = {"honor": "荣誉", "competition": "竞赛", "practice": "实践", "paper": "论文", "achievement": "成果"}
    record_type_str = args.get("record_type", "honor")
    record_type = type_map.get(record_type_str, RecordType.HONOR)
    title = args.get("title", "")
    from datetime import date as date_type
    record_date = args.get("date") or date_type.today().isoformat()
    record = GrowthRecord(
        student_id=user.id,
        type=record_type,
        title=title,
        description=args.get("description", ""),
        date=record_date,
        honor_level=args.get("honor_level"),
        organizer=args.get("organizer"),
        competition_level=args.get("competition_level"),
        practice_type=args.get("practice_type"),
        paper_type=args.get("paper_type"),
        paper_name=args.get("paper_name"),
        first_author=args.get("first_author"),
        achievement_type=args.get("achievement_type"),
        achievement_name=args.get("achievement_name"),
        attachment_url=args.get("attachment_url"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "success": True, "record_id": record.id,
        "title": record.title, "type": type_names.get(record_type_str, record_type_str),
        "message": f"📝 已记录到成长档案：{record.title}"
    }


def _update_project_stage(db: Session, args: dict, user: User, conv_id: int | None = None) -> dict:
    if not conv_id:
        return {"success": False, "message": "未找到当前对话"}
    conv = db.query(Conversation).filter(Conversation.id == conv_id, Conversation.user_id == user.id).first()
    if not conv:
        return {"success": False, "message": "未找到项目对话"}
    new_stage = args.get("stage", "")
    conv.project_stage = new_stage
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "message": f"✅ 项目阶段已更新为：{new_stage}", "stage": new_stage}


def _submit_service_request(db: Session, args: dict, user: User) -> dict:
    title = args.get("title", "")
    content = args.get("content", "")
    missing = []
    if not title:
        missing.append("title（申请标题）")
    if not content:
        missing.append("content（内容详情）")
    if missing:
        return {"success": False, "message": f"缺少必要参数：{', '.join(missing)}"}
    ticket = ServiceTicket(
        applicant_id=user.id,
        type=args.get("request_type", "other"),
        title=title,
        content=content,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {
        "success": True, "ticket_id": ticket.id,
        "message": f"📋 申请已提交（编号：{ticket.id}），等待审批。"
    }


def _query_schedule(db: Session, args: dict, user: User) -> dict:
    courses = db.query(Course).filter(Course.student_id == user.id).order_by(Course.day_of_week, Course.start_period).all()
    if not courses:
        return {"message": "暂无课表信息", "courses": []}
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    result = []
    for c in courses:
        result.append({
            "name": c.name, "teacher": c.teacher, "location": c.location,
            "day": day_names[c.day_of_week - 1] if 1 <= c.day_of_week <= 7 else f"周{c.day_of_week}",
            "period": f"第{c.start_period}-{c.end_period}节",
            "weeks": f"第{c.week_start}-{c.week_end}周",
        })
    return {"message": f"共{len(result)}门课程", "courses": result}


def _query_grades(db: Session, args: dict, user: User) -> dict:
    grades = db.query(Grade).filter(Grade.student_id == user.id).order_by(Grade.semester.desc()).all()
    if not grades:
        return {"message": "暂无成绩信息", "grades": []}
    result = []
    total_credits = 0
    total_weighted = 0.0
    for g in grades:
        result.append({"course_name": g.course_name, "score": g.score, "credit": g.credit, "gpa": g.gpa, "semester": g.semester})
        total_credits += g.credit
        total_weighted += g.gpa * g.credit
    avg_gpa = round(total_weighted / total_credits, 2) if total_credits > 0 else 0
    return {"message": f"共{len(result)}门课程，平均GPA：{avg_gpa}", "grades": result, "avg_gpa": avg_gpa}


def _query_exams(db: Session, args: dict, user: User) -> dict:
    exams = db.query(Exam).filter(Exam.student_id == user.id).order_by(Exam.exam_date).all()
    if not exams:
        return {"message": "暂无考试安排", "exams": []}
    result = []
    for e in exams:
        result.append({"course_name": e.course_name, "exam_date": str(e.exam_date), "start_time": str(e.start_time), "end_time": str(e.end_time), "location": e.location})
    return {"message": f"共{len(result)}门考试", "exams": result}


def _query_knowledge(db: Session, args: dict, user: User) -> dict:
    query = args.get("query", "")
    from app.services.knowledge_service import _escape_like
    safe_q = _escape_like(query)
    items = db.query(KnowledgeItem).filter(
        or_(
            KnowledgeItem.question.like(f"%{safe_q}%", escape="\\"),
            KnowledgeItem.answer.like(f"%{safe_q}%", escape="\\"),
            KnowledgeItem.tags.like(f"%{safe_q}%", escape="\\"),
        )
    ).limit(5).all()
    if not items:
        return {"message": "未找到相关信息", "items": []}
    return {"message": f"找到{len(items)}条相关信息", "items": [{"category": i.category, "question": i.question, "answer": i.answer} for i in items]}


def _query_sceneries(db: Session, args: dict, user: User) -> dict:
    query = db.query(CampusScenery)
    area = args.get("area")
    if area:
        query = query.filter(CampusScenery.area == area)
    items = query.all()
    if not items:
        return {"message": "暂无风景信息", "sceneries": []}
    return {"message": f"共{len(items)}个景点", "sceneries": [{"title": s.title, "description": s.description, "location": s.location} for s in items]}


def _query_announcements(db: Session, args: dict, user: User) -> dict:
    from app.utils.announcement_parser import parse_announcement_list
    try:
        resp = httpx.get("https://jwc.mycc.edu.cn/jwgl/tzgg.htm", timeout=10, follow_redirects=True)
        resp.encoding = "utf-8"
        parsed = parse_announcement_list(resp.text)
        items = [{"title": p.title, "date": p.date} for p in parsed]
        return {"message": f"教务处最新通知（共{len(items)}条）", "announcements": items[:10]}
    except Exception as e:
        return {"message": "通知获取失败", "announcements": []}


# ============ 数据分析工具 ============


def _analyze_grades(db: Session, args: dict, user: User) -> dict:
    grades = db.query(Grade).filter(Grade.student_id == user.id).order_by(Grade.semester.desc()).all()
    if not grades:
        return {"message": "暂无成绩数据"}
    grades_data = [{"course": g.course_name, "score": g.score, "gpa": g.gpa, "credit": g.credit, "semester": g.semester} for g in grades]
    semesters = sorted(set(g.semester for g in grades), reverse=True)
    return {
        "type": "grades",
        "data": {"courses": grades_data, "total": len(grades_data), "latest_semester": semesters[0] if semesters else ""},
        "message": f"共{len(grades_data)}门课程成绩，请根据以上数据进行分析并给出建议"
    }


def _analyze_schedule(db: Session, args: dict, user: User) -> dict:
    courses = db.query(Course).filter(Course.student_id == user.id).order_by(Course.day_of_week, Course.start_period).all()
    if not courses:
        return {"message": "暂无课表数据"}
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    schedule_data = [{"name": c.name, "day": day_names[c.day_of_week - 1] if 1 <= c.day_of_week <= 7 else f"周{c.day_of_week}",
                      "period": f"第{c.start_period}-{c.end_period}节", "location": c.location} for c in courses]
    return {
        "type": "schedule",
        "data": {"courses": schedule_data, "total": len(schedule_data)},
        "message": f"共{len(schedule_data)}门课程，请根据以上课表给出学习规划建议"
    }


def _analyze_growth(db: Session, args: dict, user: User) -> dict:
    records = db.query(GrowthRecord).filter(GrowthRecord.student_id == user.id).order_by(GrowthRecord.date.desc()).all()
    if not records:
        return {"message": "暂无成长记录"}
    type_names = {"honor": "荣誉", "competition": "竞赛", "practice": "实践", "paper": "论文", "achievement": "成果"}
    records_data = [{"title": r.title, "type": type_names.get(safe_enum_str(r.type, str(r.type)), str(r.type)), "date": str(r.date)} for r in records[:20]]
    return {
        "type": "growth",
        "data": {"records": records_data, "total": len(records_data)},
        "message": f"共{len(records_data)}条成长记录，请根据以上数据给出综合能力评估和发展建议"
    }

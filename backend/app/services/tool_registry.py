import json, re, httpx
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.utils.enum_helpers import safe_enum_val, safe_enum_str
from app.models.user import User, UserRole
from app.models.academic import Course, Grade, Exam
from bs4 import BeautifulSoup
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.growth import GrowthRecord, RecordType
from app.models.service import ServiceTicket, TicketType
from app.models.knowledge import KnowledgeItem
from app.models.campus import CampusScenery
from app.models.conversation import Conversation, PROJECT_STAGES
from app.models.crisis import AIDialogSummary, CrisisLevel
from sqlalchemy import or_, func


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_leave",
            "description": "创建请假申请。当学生表达请假意图时（如'请假'、'想请假'、'参加比赛需要请假'等），提取信息并自动创建请假申请",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "请假开始日期，格式YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "请假结束日期，格式YYYY-MM-DD"},
                    "reason": {"type": "string", "description": "请假原因"},
                    "leave_type": {"type": "string", "enum": ["competition", "sick", "personal", "other"], "description": "请假类型"}
                },
                "required": ["start_date", "end_date", "reason", "leave_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_growth_record",
            "description": "提取成长记录信息（不保存）。当学生提到获得了荣誉、竞赛获奖、取得奖项、参与实践、发表论文、取得成果，或上传了证明材料时，调用此工具提取信息，然后将提取结果展示给学生确认",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "记录标题"},
                    "record_type": {"type": "string", "enum": ["honor", "competition", "practice", "paper", "achievement"], "description": "类型：honor荣誉/competition竞赛/practice实践/paper论文/achievement成果"},
                    "description": {"type": "string", "description": "详细描述，从材料中提取关键信息，不要编造"},
                    "date": {"type": "string", "description": "发生日期，格式YYYY-MM-DD，从材料中提取，提取不到则留空"},
                    "honor_level": {"type": "string", "description": "荣誉等级：校级/省级/国家级/国际级"},
                    "organizer": {"type": "string", "description": "竞赛主办方"},
                    "competition_level": {"type": "string", "description": "竞赛等级：校级/省级/国家级/国际级"},
                    "practice_type": {"type": "string", "description": "实践类型：社会志愿活动/三下乡/支教/西部计划/筑梦扬帆计划/其他社会实践"},
                    "paper_type": {"type": "string", "description": "期刊类型：普刊/核心期刊/SCI/EI/顶刊/会议论文"},
                    "paper_name": {"type": "string", "description": "论文题目"},
                    "first_author": {"type": "string", "description": "第一作者"},
                    "achievement_type": {"type": "string", "description": "成果类型：发明专利/实用新型专利/软件著作权等"},
                    "achievement_name": {"type": "string", "description": "成果名称"},
                    "attachment_url": {"type": "string", "description": "证明材料URL，如果有上传文件则填写"}
                },
                "required": ["title", "record_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_growth_record",
            "description": "确认并保存成长记录。学生确认信息无误后调用此工具，将成长记录正式保存到数据库",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "记录标题"},
                    "record_type": {"type": "string", "enum": ["honor", "competition", "practice", "paper", "achievement"], "description": "类型"},
                    "description": {"type": "string", "description": "详细描述"},
                    "date": {"type": "string", "description": "发生日期，格式YYYY-MM-DD"},
                    "honor_level": {"type": "string", "description": "荣誉等级"},
                    "organizer": {"type": "string", "description": "竞赛主办方"},
                    "competition_level": {"type": "string", "description": "竞赛等级"},
                    "practice_type": {"type": "string", "description": "实践类型"},
                    "paper_type": {"type": "string", "description": "期刊类型"},
                    "paper_name": {"type": "string", "description": "论文题目"},
                    "first_author": {"type": "string", "description": "第一作者"},
                    "achievement_type": {"type": "string", "description": "成果类型"},
                    "achievement_name": {"type": "string", "description": "成果名称"},
                    "attachment_url": {"type": "string", "description": "证明材料URL"}
                },
                "required": ["title", "record_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_project_stage",
            "description": "更新项目对话的当前阶段进度。当项目对话中用户完成了当前阶段目标时，调用此工具推进到下一阶段",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {"type": "string", "description": "新的阶段名称，如'方案设计'、'实施优化'"}
                },
                "required": ["stage"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_service_request",
            "description": "提交办事服务申请（在校证明、调宿申请等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "申请标题"},
                    "content": {"type": "string", "description": "申请内容详情"},
                    "request_type": {"type": "string", "enum": ["certificate", "other"], "description": "申请类型"}
                },
                "required": ["title", "content", "request_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_schedule",
            "description": "查询学生的课程表信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "查询日期，格式YYYY-MM-DD，不传则查本周"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_grades",
            "description": "查询学生的成绩和GPA信息",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_exams",
            "description": "查询学生的考试安排",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "查询校园知识库（办事流程、规章制度、校园导航等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询关键词"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_sceneries",
            "description": "查询校园风景信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "area": {"type": "string", "enum": ["anzhou", "youxian"], "description": "校区：anzhou安州/youxian游仙，不传则查全部"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_announcements",
            "description": "查询教务处官网最新通知公告（实时抓取）",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_grades",
            "description": "查询学生成绩数据用于学情分析，包括各科成绩、GPA、学分等。调用后根据返回数据进行分析",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_schedule",
            "description": "查询学生课程表数据用于学习规划分析。调用后根据返回的课表数据给出建议",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_growth",
            "description": "查询学生成长档案数据用于综合能力评估。调用后根据返回的成长记录给出建议",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]


# ============ Teacher Tools ============

TEACHER_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_pending_leaves",
            "description": "查询名下学生待审批的请假申请。教师说'查看待批请假'、'有哪些请假'时调用",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_students",
            "description": "查询教师名下的学生列表及基本信息（成绩、成长记录数、危机等级等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "搜索关键词（姓名/学号/学院），不传则查全部"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_crisis_alerts",
            "description": "查询名下学生的心理危机预警列表。教师说'查看预警'、'有危机预警吗'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "resolved": {"type": "boolean", "description": "是否只看已处理的，不传则看全部"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "approve_leave",
            "description": "审批请假申请（通过或驳回）。教师说'批准请假'、'同意'、'驳回'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_id": {"type": "integer", "description": "请假申请ID"},
                    "action": {"type": "string", "enum": ["approve", "reject"], "description": "approve通过/reject驳回"},
                    "reject_reason": {"type": "string", "description": "驳回原因（驳回时必填）"}
                },
                "required": ["leave_id", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_student_detail",
            "description": "查看某个学生的详细信息（成长记录、项目、危机预警、请假记录等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_name": {"type": "string", "description": "学生姓名"}
                },
                "required": ["student_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_growth_stats",
            "description": "查看名下学生的成长统计数据（各类型记录数量）",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "查询校园知识库（办事流程、规章制度、校园导航等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查询关键词"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_announcements",
            "description": "查询教务处官网最新通知公告（实时抓取）",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_leave",
            "description": "查询请假申请的详细信息用于审批分析，包括学生信息、请假原因、时间等。教师说'分析这个请假'时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "leave_id": {"type": "integer", "description": "请假申请ID"}
                },
                "required": ["leave_id"]
            }
        }
    },
]


async def execute_tool(name: str, args: dict, user: User, conv_id: int | None = None) -> dict:
    db = SessionLocal()
    try:
        handler = {
            "create_leave": _create_leave,
            "create_growth_record": _create_growth_record,
            "confirm_growth_record": _confirm_growth_record,
            "update_project_stage": lambda db, a, u: _update_project_stage(db, a, u, conv_id),
            "submit_service_request": _submit_service_request,
            "query_schedule": _query_schedule,
            "query_grades": _query_grades,
            "query_exams": _query_exams,
            "query_knowledge": _query_knowledge,
            "query_sceneries": _query_sceneries,
            "query_announcements": _query_announcements,
            "analyze_grades": _analyze_grades,
            "analyze_schedule": _analyze_schedule,
            "analyze_growth": _analyze_growth,
            # 教师工具
            "query_pending_leaves": _query_pending_leaves,
            "analyze_leave": _analyze_leave,
            "query_students": _query_students,
            "query_crisis_alerts": _query_crisis_alerts,
            "approve_leave": _approve_leave,
            "query_student_detail": _query_student_detail,
            "query_growth_stats": _query_growth_stats,
        }
        fn = handler.get(name)
        if not fn:
            return {"error": f"未知工具: {name}"}
        result = fn(db, args, user)
        if hasattr(result, '__await__'):
            return await result
        return result
    finally:
        db.close()


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
    items = db.query(KnowledgeItem).filter(
        or_(KnowledgeItem.question.like(f"%{query}%"), KnowledgeItem.answer.like(f"%{query}%"), KnowledgeItem.tags.like(f"%{query}%"))
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


# ============ Teacher Tool Handlers ============

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
        like = f"%{search}%"
        query = query.filter(or_(User.name.like(like), User.username.like(like), User.college.like(like)))
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
        student = db.query(User).filter(
            User.name.like(f"%{student_name}%"), User.role == UserRole.STUDENT, User.tutor_id == user.id
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

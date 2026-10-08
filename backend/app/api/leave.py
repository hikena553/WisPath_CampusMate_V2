import json
import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.teacher_task import TaskSourceType
from app.schemas.leave import (
    LeaveApprove,
    LeaveRequestCreate,
    LeaveRequestOut,
    LeaveStats,
    LeaveStatsItem,
)
from app.services import teacher_task_service
from app.services import learning_event_service
from app.services.llm_service import _get_client, _get_llm_config
from app.utils.enum_helpers import safe_enum_val, safe_enum_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leave", tags=["leave"])

# 同生频繁请假识别：窗口期内非驳回请假达到阈值即生成跟进提醒
FREQUENT_LEAVE_THRESHOLD = 3
FREQUENT_LEAVE_WINDOW_DAYS = 30


def _maybe_alert_frequent_leave(db: Session, teacher_id: int, student: User, leave: LeaveRequest) -> None:
    """同生频繁请假 → 生成 alert 待办任务。

    幂等：任务唯一键为 (alert, student_id, teacher_id)，同一学生只保留一条未办结提醒，
    不会因每次审批重复堆积。
    """
    db.commit()
    window_start = datetime.now() - timedelta(days=FREQUENT_LEAVE_WINDOW_DAYS)
    recent = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == student.id,
        LeaveRequest.created_at >= window_start,
        LeaveRequest.status != LeaveStatus.REJECTED,
    ).count()
    if recent < FREQUENT_LEAVE_THRESHOLD:
        return
    try:
        teacher_task_service.create_task(
            db,
            teacher_id=teacher_id,
            title=f"频繁请假跟进：{student.name}",
            detail=f"近{FREQUENT_LEAVE_WINDOW_DAYS}天内已有{recent}次请假，建议了解原因并跟踪学业与心理状态",
            student_id=student.id,
            due_at=date.today() + timedelta(days=1),
            source_type=TaskSourceType.ALERT,
            source_id=student.id,
        )
    except Exception:  # 提醒失败不得影响审批主流程
        logger.warning("频繁请假提醒任务创建失败 student=%s", student.id, exc_info=True)


def _to_out(r: LeaveRequest, student_name: str = "") -> LeaveRequestOut:
    return LeaveRequestOut(
        id=r.id,
        student_id=r.student_id,
        student_name=student_name,
        start_date=r.start_date,
        end_date=r.end_date,
        reason=r.reason,
        leave_type=safe_enum_val(r.leave_type),
        status=safe_enum_val(r.status),
        reject_reason=r.reject_reason,
        return_confirmed=bool(r.return_confirmed),
        return_confirmed_at=r.return_confirmed_at.isoformat() if r.return_confirmed_at else None,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


@router.get("/my", response_model=list[LeaveRequestOut])
def list_my_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requests = db.query(LeaveRequest).filter(LeaveRequest.student_id == user.id).order_by(LeaveRequest.created_at.desc()).all()
    result = []
    for r in requests:
        result.append(_to_out(r, user.name))
    return result


@router.post("/create", response_model=LeaveRequestOut)
def create_leave(req: LeaveRequestCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    if req.start_date < today:
        raise HTTPException(status_code=400, detail="开始日期不能早于今天")
    if req.end_date < req.start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if (req.end_date - req.start_date).days > 14:
        raise HTTPException(status_code=400, detail="请假时长不能超过15天")
    leave = LeaveRequest(
        student_id=user.id,
        start_date=req.start_date,
        end_date=req.end_date,
        reason=req.reason,
        leave_type=req.leave_type,
    )
    db.add(leave)
    db.flush()
    # 学情数据底座：单点写入（旁路，失败不影响主流程）
    learning_event_service.emit(
        db,
        actor_id=user.id,
        verb="leave.apply",
        object_type="leave",
        object_id=leave.id,
        context={
            "leave_type": safe_enum_val(leave.leave_type),
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "days": (req.end_date - req.start_date).days + 1,
        },
    )
    db.commit()
    db.refresh(leave)
    return _to_out(leave, user.name)


@router.delete("/{leave_id}")
def delete_leave(leave_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id, LeaveRequest.student_id == user.id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="请假申请不存在")
    db.delete(leave)
    db.commit()
    return {"message": "已删除"}


@router.get("/pending", response_model=list[LeaveRequestOut])
def list_pending(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.PENDING)
    if user.role != UserRole.ADMIN:
        student_ids = [s.id for s in db.query(User).filter(User.tutor_id == user.id).all()]
        if student_ids:
            query = query.filter(LeaveRequest.student_id.in_(student_ids))
        else:
            query = query.filter(False)
    requests = query.order_by(LeaveRequest.created_at.desc()).all()
    result = []
    for r in requests:
        student = db.query(User).filter(User.id == r.student_id).first()
        result.append(_to_out(r, student.name if student else ""))
    return result


@router.post("/{leave_id}/review")
def review_leave(leave_id: int, req: LeaveApprove, user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="请假申请不存在")
    if user.role != UserRole.ADMIN:
        student = db.query(User).filter(User.id == leave.student_id).first()
        if not student or student.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权审批该请假")
    if req.action == "approve":
        leave.status = LeaveStatus.APPROVED
        leave.tutor_id = user.id
    elif req.action == "reject":
        leave.status = LeaveStatus.REJECTED
        leave.tutor_id = user.id
        leave.reject_reason = req.reject_reason or ""
    else:
        raise HTTPException(status_code=400, detail="无效操作")
    student = db.query(User).filter(User.id == leave.student_id).first()
    if student:
        from app.models.notification import NotificationType
        from app.services.notification_service import send_notification
        send_notification(
            db, student.id,
            title="请假审批结果",
            content=(
                f"你的请假申请（{safe_enum_val(leave.leave_type)}，"
                f"{leave.start_date}~{leave.end_date}）已{'通过' if leave.status.value == 'approved' else '未通过'}"
                + (f"，原因：{leave.reject_reason}" if leave.status.value == "rejected" else "")
            ),
            notification_type=NotificationType.LEAVE,
            link="/student/workbench",
            related_id=leave.id,
            sender_id=user.id,
            sms_template="请假审批结果通知",
        )
    else:
        db.commit()
    # 闭环（模块 5）：同生频繁请假 → 生成 alert 跟进任务
    if student and leave.status == LeaveStatus.APPROVED:
        _maybe_alert_frequent_leave(db, student.tutor_id or user.id, student, leave)
    return {"message": f"已{req.action}"}


@router.get("/all", response_model=list[LeaveRequestOut])
def list_all_requests(status: str | None = None, user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    query = db.query(LeaveRequest)
    if user.role != UserRole.ADMIN:
        student_ids = [s.id for s in db.query(User).filter(User.tutor_id == user.id).all()]
        if student_ids:
            query = query.filter(LeaveRequest.student_id.in_(student_ids))
        else:
            query = query.filter(False)
    if status:
        query = query.filter(LeaveRequest.status == status)
    requests = query.order_by(LeaveRequest.created_at.desc()).all()
    result = []
    for r in requests:
        student = db.query(User).filter(User.id == r.student_id).first()
        result.append(_to_out(r, student.name if student else ""))
    return result


@router.get("/stats", response_model=LeaveStats)
def leave_stats(user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    """请假统计报表：按类型 / 按班级聚合，供审批页统计 Tab 使用。"""
    query = db.query(LeaveRequest)
    students = db.query(User)
    if user.role != UserRole.ADMIN:
        students = students.filter(User.tutor_id == user.id)
    student_map = {s.id: s for s in students.all()}
    if user.role != UserRole.ADMIN:
        if student_map:
            query = query.filter(LeaveRequest.student_id.in_(list(student_map.keys())))
        else:
            query = query.filter(False)

    requests = query.all()
    type_labels = {
        "competition": "竞赛", "sick": "病假", "personal": "事假", "other": "其他",
    }
    by_type: dict[str, LeaveStatsItem] = {}
    by_class: dict[str, LeaveStatsItem] = {}
    stats = LeaveStats()

    for r in requests:
        status = safe_enum_val(r.status)
        ltype = safe_enum_val(r.leave_type)
        stats.total += 1
        if status == "approved":
            stats.approved += 1
            if not r.return_confirmed:
                stats.awaiting_return += 1
        elif status == "rejected":
            stats.rejected += 1
        else:
            stats.pending += 1

        tkey = ltype or "other"
        by_type.setdefault(tkey, LeaveStatsItem(key=tkey, label=type_labels.get(tkey, "其他")))
        _bump(by_type[tkey], status)

        student = student_map.get(r.student_id)
        ckey = (student.class_name if student and student.class_name else "未分班")
        by_class.setdefault(ckey, LeaveStatsItem(key=ckey, label=ckey))
        _bump(by_class[ckey], status)

    stats.by_type = sorted(by_type.values(), key=lambda x: x.total, reverse=True)
    stats.by_class = sorted(by_class.values(), key=lambda x: x.total, reverse=True)
    return stats


def _bump(item: LeaveStatsItem, status: str) -> None:
    item.total += 1
    if status == "approved":
        item.approved += 1
    elif status == "rejected":
        item.rejected += 1
    else:
        item.pending += 1


@router.post("/{leave_id}/confirm-return")
def confirm_return(leave_id: int, user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    """销假确认：审批通过的请假，学生返校后由教师确认，闭环结束。"""
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="请假申请不存在")
    if user.role != UserRole.ADMIN:
        student = db.query(User).filter(User.id == leave.student_id).first()
        if not student or student.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权操作该请假")
    if safe_enum_val(leave.status) != "approved":
        raise HTTPException(status_code=400, detail="仅已通过的请假可确认返校")
    if leave.return_confirmed:
        return {"message": "已确认返校", "return_confirmed": True}

    leave.return_confirmed = True
    leave.return_confirmed_at = datetime.now()
    db.commit()

    student = db.query(User).filter(User.id == leave.student_id).first()
    if student:
        from app.models.notification import NotificationType
        from app.services.notification_service import send_notification
        send_notification(
            db, student.id,
            title="销假确认",
            content=f"你的请假（{leave.start_date}~{leave.end_date}）已完成销假确认，欢迎返校。",
            notification_type=NotificationType.LEAVE,
            link="/student/workbench",
            related_id=leave.id,
            sender_id=user.id,
        )
    return {"message": "已确认返校", "return_confirmed": True}


@router.get("/{id}/analyze")
async def analyze_leave(id: int, user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)), db: Session = Depends(get_db)):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="请假申请不存在")
    student = db.query(User).filter(User.id == leave.student_id).first()
    prompt = f"""你是一位校园审批助手。请分析以下请假申请，给出审批建议和理由。

学生：{student.name if student else "未知"}
类型：{safe_enum_val(leave.leave_type)}
时间：{leave.start_date} 至 {leave.end_date}
原因：{leave.reason}

要求：
1. suggestion 必须是 "approve" 或 "reject"
2. reason 必须用中文给出具体的分析理由（至少20字）
3. 只返回JSON，不要其他内容

格式：{{"suggestion": "approve", "reason": "具体分析理由..."}}"""
    try:
        config = _get_llm_config()
        resp = await _get_client().chat.completions.create(
            model=config['model'], messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=300,
        )
        content = resp.choices[0].message.content or ""
        logger.info("[AI分析原始返回] leave_id=%d, content=%s", id, content[:300])
        # 去除 markdown 代码块包裹
        import re
        cleaned = re.sub(r"```(?:json)?\s*", "", content).strip().rstrip("`")
        try:
            result = json.loads(cleaned)
            # 确保 reason 不为空
            if not result.get("reason"):
                result["reason"] = content[:200] if content else "AI 已给出审批建议"
            logger.info("[AI分析解析结果] leave_id=%d, result=%s", id, result)
            return result
        except json.JSONDecodeError:
            logger.warning("[AI分析JSON解析失败] leave_id=%d, cleaned=%s", id, cleaned[:200])
            return {"suggestion": "approve", "reason": content[:200] if content else "AI 分析暂时不可用"}
    except Exception as e:
        return {"suggestion": "approve", "reason": "AI分析暂时不可用，请自行判断"}

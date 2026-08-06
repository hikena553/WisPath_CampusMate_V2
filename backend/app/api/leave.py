import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.leave import LeaveRequest, LeaveStatus
from app.schemas.leave import LeaveRequestCreate, LeaveRequestOut, LeaveApprove
from app.services.llm_service import _get_client, _get_llm_config
from app.utils.enum_helpers import safe_enum_val, safe_enum_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/leave", tags=["leave"])


@router.get("/my", response_model=list[LeaveRequestOut])
def list_my_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requests = db.query(LeaveRequest).filter(LeaveRequest.student_id == user.id).order_by(LeaveRequest.created_at.desc()).all()
    result = []
    for r in requests:
        student = db.query(User).filter(User.id == r.student_id).first()
        result.append(LeaveRequestOut(
            id=r.id,
            student_id=r.student_id,
            student_name=student.name if student else "",
            start_date=r.start_date,
            end_date=r.end_date,
            reason=r.reason,
            leave_type=safe_enum_val(r.leave_type),
            status=safe_enum_val(r.status),
            reject_reason=r.reject_reason,
            created_at=r.created_at.isoformat() if r.created_at else "",
        ))
    return result


@router.post("/create", response_model=LeaveRequestOut)
def create_leave(req: LeaveRequestCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    leave = LeaveRequest(
        student_id=user.id,
        start_date=req.start_date,
        end_date=req.end_date,
        reason=req.reason,
        leave_type=req.leave_type,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return LeaveRequestOut(
        id=leave.id,
        student_id=leave.student_id,
        student_name=user.name,
        start_date=leave.start_date,
        end_date=leave.end_date,
        reason=leave.reason,
        leave_type=safe_enum_val(leave.leave_type),
        status=safe_enum_val(leave.status),
        reject_reason=leave.reject_reason,
        created_at=leave.created_at.isoformat() if leave.created_at else "",
    )


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
        result.append(LeaveRequestOut(
            id=r.id,
            student_id=r.student_id,
            student_name=student.name if student else "",
            start_date=r.start_date,
            end_date=r.end_date,
            reason=r.reason,
            leave_type=safe_enum_val(r.leave_type),
            status=safe_enum_val(r.status),
            reject_reason=r.reject_reason,
            created_at=r.created_at.isoformat() if r.created_at else "",
        ))
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
        leave.reject_reason = req.reject_reason
    else:
        raise HTTPException(status_code=400, detail="无效操作")
    db.commit()
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
        result.append(LeaveRequestOut(
            id=r.id, student_id=r.student_id, student_name=student.name if student else "",
            start_date=r.start_date, end_date=r.end_date, reason=r.reason,
            leave_type=safe_enum_val(r.leave_type),
            status=safe_enum_val(r.status),
            reject_reason=r.reject_reason,
            created_at=r.created_at.isoformat() if r.created_at else "",
        ))
    return result


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

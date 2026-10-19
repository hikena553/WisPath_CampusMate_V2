from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.service import ServiceTicket, TicketStatus, TERMINAL_TICKET_STATUSES
from app.models.user import User, UserRole
from app.schemas.service import TicketCreate, TicketOut, TicketApprove

router = APIRouter(prefix="/api/service", tags=["service"])


# 审批视角可操作的工单状态（PENDING/中间态 PROCESSING 均可审批）
_APPROVABLE_STATUSES = {TicketStatus.PENDING, TicketStatus.PROCESSING}


@router.post("/tickets", response_model=TicketOut)
def create_ticket(req: TicketCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = ServiceTicket(
        applicant_id=user.id,
        applicant_name=req.applicant_name or user.name,
        applicant_no=req.applicant_no or user.username,
        applicant_college=req.applicant_college or (user.college or ""),
        type=req.type,
        title=req.title,
        content=req.content,
        form_data=req.form_data,
        attachments=req.attachments,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(
    status: str | None = None,
    scope: str = Query("queue", description="审批视角：queue=共享待办队列 / mine=我受理的"),
    student_id: int | None = Query(None, description="按申请学生过滤，闭环用"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ServiceTicket)
    if user.role in (UserRole.TEACHER, UserRole.ADMIN):
        if status:
            # 显式指定状态：待办理用于办理，终态（approved / rejected）用于审批留痕回看
            if status not in {s.value for s in TicketStatus}:
                raise HTTPException(status_code=400, detail="status 取值不合法")
            query = query.filter(ServiceTicket.status == status)
        else:
            # 不带状态时是「共享待办队列」（含中间态 PROCESSING），先到先审
            query = query.filter(ServiceTicket.status.in_([s.value for s in _APPROVABLE_STATUSES]))
        if scope == "mine":
            # 我受理的：责任人是我（受理动作把 approver 落给我）——参考 osTicket「My Tickets」/ Zammad Owner
            query = query.filter(ServiceTicket.approver_id == user.id)
        elif scope != "queue":
            raise HTTPException(status_code=400, detail="scope 仅支持 queue / mine")
        if student_id is not None:
            query = query.filter(ServiceTicket.applicant_id == student_id)
        # 待办按提交时间先到先审；终态按提交时间倒序，最近处理的排前面
        order = ServiceTicket.created_at.asc() if status is None else ServiceTicket.created_at.desc()
        return query.order_by(order).all()
    # 学生/其他视角：仅本人申请记录
    query = query.filter(ServiceTicket.applicant_id == user.id)
    if status:
        query = query.filter(ServiceTicket.status == status)
    return query.order_by(ServiceTicket.created_at.desc()).all()


@router.put("/tickets/{ticket_id}/claim", response_model=TicketOut)
def claim_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """受理（认领）工单：待受理 → 处理中，责任人落到受理人名下。

    对应成熟服务台的责任人模型（osTicket Agent/Assignee、Zammad Ticket Owner、
    FreeScout Assignee）：先认领再办理，队列里其他人能看到「谁在处理」，
    避免同一条申请被多人重复处理。
    """
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="仅教师/管理员可受理工单")
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.status in TERMINAL_TICKET_STATUSES:
        raise HTTPException(status_code=400, detail="工单已办结，终态不可再受理")
    if ticket.status not in _APPROVABLE_STATUSES:
        raise HTTPException(status_code=400, detail="当前工单状态不可受理")
    if ticket.approver_id and ticket.approver_id != user.id:
        raise HTTPException(status_code=400, detail=f"工单已由 {ticket.approver_name or '他人'} 受理")
    ticket.status = TicketStatus.PROCESSING
    ticket.approver_id = user.id
    ticket.approver_name = user.name
    db.commit()
    db.refresh(ticket)
    return ticket


@router.put("/tickets/{ticket_id}/approve")
def approve_ticket(ticket_id: int, req: TicketApprove, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="仅教师/管理员可审批工单")
    if req.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 必须为 approve 或 reject")
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.status in TERMINAL_TICKET_STATUSES:
        raise HTTPException(status_code=400, detail="工单已审批，终态不可再变更")
    if ticket.status not in _APPROVABLE_STATUSES:
        raise HTTPException(status_code=400, detail="当前工单状态不可审批")
    ticket.status = TicketStatus.APPROVED if req.action == "approve" else TicketStatus.REJECTED
    ticket.approver_id = user.id
    ticket.approver_name = user.name
    if req.comment:
        ticket.review_comment = req.comment.strip()
    # 工单进度推送：审批后站内通知申请人
    from app.models.notification import NotificationType
    from app.services.notification_service import send_notification
    send_notification(
        db, ticket.applicant_id,
        title="工单审批结果",
        content=f"你的工单「{ticket.title}」审批结果：{'已通过' if ticket.status.value == 'approved' else '未通过'}",
        notification_type=NotificationType.APPROVAL,
        link="/student/workbench",
        related_id=ticket.id,
        sender_id=user.id,
        sms_template="工单审批结果通知",
    )
    return {"message": f"ticket {req.action}d"}


@router.put("/tickets/{ticket_id}/cancel")
def cancel_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(ServiceTicket).filter(
        ServiceTicket.id == ticket_id,
        ServiceTicket.applicant_id == user.id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    if ticket.status != TicketStatus.PENDING:
        raise HTTPException(status_code=400, detail="只能撤销待审批的申请")
    db.delete(ticket)
    db.commit()
    return {"message": "申请已撤销"}
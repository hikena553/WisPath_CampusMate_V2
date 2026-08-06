from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.service import ServiceTicket, TicketStatus
from app.models.user import User
from app.schemas.service import TicketCreate, TicketOut, TicketApprove

router = APIRouter(prefix="/api/service", tags=["service"])


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
def list_tickets(status: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(ServiceTicket).filter(ServiceTicket.applicant_id == user.id)
    if status:
        query = query.filter(ServiceTicket.status == status)
    return query.order_by(ServiceTicket.created_at.desc()).all()


@router.put("/tickets/{ticket_id}/approve")
def approve_ticket(ticket_id: int, req: TicketApprove, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    ticket.status = TicketStatus.APPROVED if req.action == "approve" else TicketStatus.REJECTED
    db.commit()
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
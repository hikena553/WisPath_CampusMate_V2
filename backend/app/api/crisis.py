from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.crisis import AIDialogSummary, InterventionType
from app.schemas.crisis import AIDialogSummaryOut, CrisisResolve, CrisisInterveneIn
from app.utils.enum_helpers import safe_enum_val

router = APIRouter(prefix="/api/crisis", tags=["crisis"])


def _filter_by_tutor(query, user, db):
    if user.role == UserRole.ADMIN:
        return query
    student_ids = [s.id for s in db.query(User).filter(User.tutor_id == user.id).all()]
    if student_ids:
        return query.filter(AIDialogSummary.student_id.in_(student_ids))
    return query.filter(False)


@router.get("/alerts", response_model=list[AIDialogSummaryOut])
def list_alerts(resolved: bool | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可查看")
    query = db.query(AIDialogSummary).order_by(AIDialogSummary.created_at.desc())
    query = _filter_by_tutor(query, user, db)
    if resolved is not None:
        query = query.filter(AIDialogSummary.resolved == resolved)
    alerts = query.all()
    result = []
    for a in alerts:
        student = db.query(User).filter(User.id == a.student_id).first()
        result.append(AIDialogSummaryOut(
            id=a.id,
            student_id=a.student_id,
            student_name=student.name if student else "",
            summary=a.summary,
            level=safe_enum_val(a.level),
            keywords_matched=a.keywords_matched,
            resolved=a.resolved,
            created_at=a.created_at.isoformat() if a.created_at else "",
            intervention_type=a.intervention_type.value if a.intervention_type else None,
            intervention_note=a.intervention_note,
            resolved_by=a.resolved_by,
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            follow_up_date=str(a.follow_up_date) if a.follow_up_date else None,
        ))
    return result


@router.get("/students/{student_id}/alerts", response_model=list[AIDialogSummaryOut])
def list_student_alerts(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可查看")
    if user.role != UserRole.ADMIN:
        student = db.query(User).filter(User.id == student_id).first()
        if not student or student.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权查看该学生的预警")
    alerts = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).all()
    student = db.query(User).filter(User.id == student_id).first()
    return [
        AIDialogSummaryOut(
            id=a.id,
            student_id=a.student_id,
            student_name=student.name if student else "",
            summary=a.summary,
            level=safe_enum_val(a.level),
            keywords_matched=a.keywords_matched,
            resolved=a.resolved,
            created_at=a.created_at.isoformat() if a.created_at else "",
            intervention_type=a.intervention_type.value if a.intervention_type else None,
            intervention_note=a.intervention_note,
            resolved_by=a.resolved_by,
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            follow_up_date=str(a.follow_up_date) if a.follow_up_date else None,
        ) for a in alerts
    ]


@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: int, req: CrisisResolve, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可操作")
    alert = db.query(AIDialogSummary).filter(AIDialogSummary.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    if user.role != UserRole.ADMIN:
        s = db.query(User).filter(User.id == alert.student_id).first()
        if not s or s.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权操作该预警")
    alert.resolved = req.resolved
    if req.resolved:
        alert.resolved_by = user.id
        alert.resolved_at = datetime.now(timezone.utc)
    else:
        alert.resolved_by = None
        alert.resolved_at = None
    db.commit()
    return {"message": "已更新"}


@router.post("/{alert_id}/intervene")
def intervene_alert(alert_id: int, req: CrisisInterveneIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可操作")
    alert = db.query(AIDialogSummary).filter(AIDialogSummary.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    if user.role != UserRole.ADMIN:
        s = db.query(User).filter(User.id == alert.student_id).first()
        if not s or s.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权操作该预警")
    try:
        alert.intervention_type = InterventionType(req.intervention_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效干预类型: {req.intervention_type}")
    alert.intervention_note = req.intervention_note
    alert.follow_up_date = datetime.strptime(req.follow_up_date, "%Y-%m-%d").date() if req.follow_up_date else None
    alert.resolved = req.resolved
    alert.resolved_by = user.id
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "干预记录已保存"}

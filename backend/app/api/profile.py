from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.profile import StudentProfileSnapshot
from app.schemas.profile import (
    ProfileSnapshotOut, ProfileTrendsOut, ProfileTrendPoint,
    CohortComparisonOut, CohortComparison,
)
from app.services.student_profile_engine import get_latest_profile, get_profile_history
from app.services.scoring import get_cohort_percentile, get_trajectory, get_risk_indicators

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/student/{student_id}", response_model=ProfileSnapshotOut | None)
def get_student_profile(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.ADMIN and user.role == UserRole.TEACHER:
        student = db.query(User).filter(User.id == student_id, User.tutor_id == user.id).first()
        if not student:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="无权查看该学生画像")
    return get_latest_profile(db, student_id)


@router.get("/student/{student_id}/trends", response_model=ProfileTrendsOut)
def get_student_trends(
    student_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role == UserRole.STUDENT and user.id != student_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权查看")
    history = get_profile_history(db, student_id, limit=30)
    trends = [
        ProfileTrendPoint(
            date=str(h.snapshot_date),
            academic_score=h.academic_score,
            psychological_risk=h.psychological_risk,
            engagement_score=h.engagement_score,
            growth_score=h.growth_score,
            overall_risk=h.overall_risk,
        ) for h in history
    ]
    trends.reverse()
    return ProfileTrendsOut(trends=trends)


@router.get("/cohort/{student_id}", response_model=CohortComparisonOut)
def get_student_cohort(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    cohort = get_cohort_percentile(db, student_id)
    comparisons = [
        CohortComparison(dimension=k, student_score=0, cohort_avg=0, percentile=v)
        for k, v in cohort.items()
    ]
    return CohortComparisonOut(comparisons=comparisons)


@router.get("/student/{student_id}/risk-indicators")
def get_student_risk_indicators(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return get_risk_indicators(db, student_id)


@router.get("/student/{student_id}/trajectory")
def get_student_trajectory(
    student_id: int,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return get_trajectory(db, student_id)


@router.post("/refresh")
def refresh_profiles(
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    import threading, asyncio
    from app.services.student_profile_engine import refresh_all_profiles
    threading.Thread(target=lambda: asyncio.run(refresh_all_profiles()), daemon=True).start()
    return {"message": "画像刷新已启动"}

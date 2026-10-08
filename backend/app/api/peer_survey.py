"""匿名问卷互评接口：问卷管理 + 匿名提交 + 聚合结果（不回传任何单条答卷）。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.peer_survey import PeerSurveyResponse, PeerSurveyStatus
from app.models.user import User, UserRole
from app.schemas.peer_survey import (
    PeerSurveyCreate,
    PeerSurveyMineItem,
    PeerSurveyOut,
    PeerSurveyResult,
    PeerSurveyStatusUpdate,
    PeerSurveySubmit,
)
from app.services import peer_survey_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/peer-surveys", tags=["peer-surveys"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/mine", response_model=list[PeerSurveyMineItem])
def my_results(user: User = Depends(_teacher_only), db: Session = Depends(get_db)):
    """我的被评结果（仅聚合，匿名）。"""
    return peer_survey_service.my_results(db, user.id)


@router.get("", response_model=list[PeerSurveyOut])
def list_surveys(
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, _ = peer_survey_service.list_surveys(db, limit=limit, offset=offset)
    # 标注当前用户是否已提交（对每个开放问卷）
    token_cache: dict[int, str] = {}
    enriched = []
    for it in items:
        token = token_cache.setdefault(it["id"], peer_survey_service.compute_token(user.id, it["id"]))
        submitted = peer_survey_service.has_submitted(db, it["id"], token)
        enriched.append({**it, "my_submitted": submitted})
    return enriched


@router.post("", response_model=PeerSurveyOut)
def create_survey(
    payload: PeerSurveyCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    survey = peer_survey_service.create_survey(
        db,
        created_by=user.id,
        title=payload.title,
        target_type=payload.target_type,
        period=payload.period,
        questions=[q.model_dump() for q in payload.questions],
        status=payload.status,
    )
    return peer_survey_service.serialize(survey)


@router.patch("/{survey_id}/status", response_model=PeerSurveyOut)
def update_status(
    survey_id: int,
    payload: PeerSurveyStatusUpdate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    survey = peer_survey_service.get_survey(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    if user.role != UserRole.ADMIN and survey.created_by != user.id:
        raise HTTPException(status_code=403, detail="只能操作本人创建的问卷")
    peer_survey_service.update_status(db, survey, payload.status)
    count = (
        db.query(PeerSurveyResponse)
        .filter(PeerSurveyResponse.survey_id == survey.id)
        .count()
    )
    return peer_survey_service.serialize(survey, count)


@router.post("/{survey_id}/responses")
def submit_response(
    survey_id: int,
    payload: PeerSurveySubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """匿名提交：不记录提交人，仅落 HMAC 令牌用于防重。"""
    survey = peer_survey_service.get_survey(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    if survey.status != PeerSurveyStatus.OPEN:
        raise HTTPException(status_code=400, detail="问卷未开放，无法提交")

    token = peer_survey_service.compute_token(user.id, survey.id)
    try:
        peer_survey_service.submit_response(
            db,
            survey=survey,
            target_teacher_id=payload.target_teacher_id,
            scores=payload.scores,
            suggestion=payload.suggestion,
            token=token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    # 提交结果不回传任何可回溯信息
    return {"message": "提交成功（匿名）"}


@router.get("/{survey_id}/result", response_model=PeerSurveyResult)
def survey_result(
    survey_id: int,
    target_teacher_id: int | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    survey = peer_survey_service.get_survey(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return peer_survey_service.aggregate(db, survey, target_teacher_id=target_teacher_id)
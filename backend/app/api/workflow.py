"""审批流程引擎接口：流程定义（管理员）+ 流程实例（发起 / 审批 / 驳回 / 撤销）。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.services import workflow_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

_staff_only = require_role(UserRole.TEACHER, UserRole.ADMIN)
_admin_only = require_role(UserRole.ADMIN)


class WorkflowNodeIn(BaseModel):
    key: str
    name: str
    approver_role: str = "teacher"


class WorkflowDefIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    biz_type: str = ""
    nodes: list[WorkflowNodeIn] = []
    is_active: bool = True


class WorkflowStartIn(BaseModel):
    def_code: str
    biz_type: str = ""
    biz_id: int | None = None


class WorkflowActionIn(BaseModel):
    comment: str = ""


# ── 流程定义 ──────────────────────────────────────────────────


@router.get("/defs")
def list_defs(
    active_only: bool = Query(default=False),
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    return workflow_engine.list_defs(db, active_only=active_only)


@router.post("/defs")
def create_def(
    payload: WorkflowDefIn,
    user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    try:
        defn = workflow_engine.create_def(
            db,
            code=payload.code,
            name=payload.name,
            nodes=[n.model_dump() for n in payload.nodes],
            biz_type=payload.biz_type,
            created_by=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return workflow_engine.serialize_def(defn)


# ── 流程实例 ──────────────────────────────────────────────────


@router.get("/instances")
def list_instances(
    mine: bool = Query(default=False),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    initiator_id = user.id if mine else None
    return workflow_engine.list_instances(db, initiator_id=initiator_id, status=status, limit=limit)


@router.post("/instances")
def start_instance(
    payload: WorkflowStartIn,
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    try:
        instance = workflow_engine.start(
            db,
            def_code=payload.def_code,
            initiator_id=user.id,
            biz_type=payload.biz_type,
            biz_id=payload.biz_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return workflow_engine.serialize_instance(db, instance)


def _load_instance(db: Session, instance_id: int):
    instance = workflow_engine.get_instance(db, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="流程实例不存在")
    return instance


@router.post("/instances/{instance_id}/approve")
def approve_instance(
    instance_id: int,
    payload: WorkflowActionIn,
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    instance = _load_instance(db, instance_id)
    try:
        workflow_engine.approve(db, instance, user, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return workflow_engine.serialize_instance(db, instance)


@router.post("/instances/{instance_id}/reject")
def reject_instance(
    instance_id: int,
    payload: WorkflowActionIn,
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    instance = _load_instance(db, instance_id)
    try:
        workflow_engine.reject(db, instance, user, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return workflow_engine.serialize_instance(db, instance)


@router.post("/instances/{instance_id}/cancel")
def cancel_instance(
    instance_id: int,
    payload: WorkflowActionIn,
    user: User = Depends(_staff_only),
    db: Session = Depends(get_db),
):
    instance = _load_instance(db, instance_id)
    try:
        workflow_engine.cancel(db, instance, user, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return workflow_engine.serialize_instance(db, instance)
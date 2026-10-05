"""审批流程引擎：四个原语 start / approve / reject / cancel。

- 节点定义来自 WorkflowDef.nodes_json，新增审批类型无需改代码；
- 每次动作写入 history（可追溯）；
- 非法流转（已结束实例再审批、越权操作）一律抛 ValueError，由 API 层转为 400/403。
"""
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowDef, WorkflowInstance, WorkflowStatus
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


def _load_nodes(defn: WorkflowDef) -> list[dict]:
    try:
        data = json.loads(defn.nodes_json or "[]")
        return data if isinstance(data, list) else []
    except (TypeError, ValueError):
        return []


def _history(instance: WorkflowInstance) -> list[dict]:
    try:
        data = json.loads(instance.history_json or "[]")
        return data if isinstance(data, list) else []
    except (TypeError, ValueError):
        return []


def _append_history(instance: WorkflowInstance, entry: dict) -> None:
    items = _history(instance)
    items.append(entry)
    instance.history_json = json.dumps(items, ensure_ascii=False)


def _serialize(instance: WorkflowInstance, defn: WorkflowDef | None = None) -> dict:
    nodes = _load_nodes(defn) if defn else []
    current = nodes[instance.current_index] if 0 <= instance.current_index < len(nodes) else None
    return {
        "id": instance.id,
        "def_id": instance.def_id,
        "def_code": defn.code if defn else "",
        "def_name": defn.name if defn else "",
        "biz_type": instance.biz_type,
        "biz_id": instance.biz_id,
        "initiator_id": instance.initiator_id,
        "status": instance.status.value if instance.status else "running",
        "current_index": instance.current_index,
        "current_node": current,
        "node_count": len(nodes),
        "history": _history(instance),
        "created_at": instance.created_at.isoformat() if instance.created_at else "",
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else "",
    }


def serialize_def(defn: WorkflowDef) -> dict:
    return {
        "id": defn.id,
        "code": defn.code,
        "name": defn.name,
        "biz_type": defn.biz_type,
        "nodes": _load_nodes(defn),
        "is_active": bool(defn.is_active),
        "created_at": defn.created_at.isoformat() if defn.created_at else "",
    }


def create_def(
    db: Session,
    *,
    code: str,
    name: str,
    nodes: list[dict],
    biz_type: str = "",
    created_by: int = 0,
) -> WorkflowDef:
    if not nodes:
        raise ValueError("流程至少需要一个审批节点")
    existing = db.query(WorkflowDef).filter(WorkflowDef.code == code).first()
    if existing:
        raise ValueError(f"流程编码已存在：{code}")
    defn = WorkflowDef(
        code=code,
        name=name,
        biz_type=biz_type,
        nodes_json=json.dumps(nodes, ensure_ascii=False),
        created_by=created_by,
    )
    db.add(defn)
    db.commit()
    db.refresh(defn)
    logger.info("[WORKFLOW] 创建流程定义 code=%s nodes=%s", code, len(nodes))
    return defn


def get_def(db: Session, def_id: int) -> WorkflowDef | None:
    return db.query(WorkflowDef).filter(WorkflowDef.id == def_id).first()


def get_def_by_code(db: Session, code: str) -> WorkflowDef | None:
    return db.query(WorkflowDef).filter(WorkflowDef.code == code).first()


def list_defs(db: Session, *, active_only: bool = False) -> list[dict]:
    query = db.query(WorkflowDef)
    if active_only:
        query = query.filter(WorkflowDef.is_active.is_(True))
    return [serialize_def(d) for d in query.order_by(WorkflowDef.id.asc()).all()]


# ── 四个原语 ──────────────────────────────────────────────────


def start(
    db: Session,
    *,
    def_code: str,
    initiator_id: int,
    biz_type: str = "",
    biz_id: int | None = None,
) -> WorkflowInstance:
    defn = get_def_by_code(db, def_code)
    if not defn or not defn.is_active:
        raise ValueError(f"流程不存在或已停用：{def_code}")
    nodes = _load_nodes(defn)
    if not nodes:
        raise ValueError("流程未定义审批节点")

    instance = WorkflowInstance(
        def_id=defn.id,
        biz_type=biz_type or defn.biz_type,
        biz_id=biz_id,
        initiator_id=initiator_id,
        current_index=0,
        status=WorkflowStatus.RUNNING,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    _append_history(
        instance,
        {
            "node": None,
            "node_name": "发起",
            "actor_id": initiator_id,
            "action": "start",
            "comment": "",
            "at": datetime.now().isoformat(),
        },
    )
    db.commit()
    db.refresh(instance)
    return instance


def _ensure_running(instance: WorkflowInstance) -> None:
    if instance.status != WorkflowStatus.RUNNING:
        raise ValueError(f"流程已{instance.status.value}，无法继续操作")


def _ensure_operator(db: Session, instance: WorkflowInstance, actor: User) -> None:
    """审批人校验：管理员放行；否则需为发起人本人或教师角色。"""
    if actor.role == UserRole.ADMIN or actor.id == instance.initiator_id:
        return
    if actor.role != UserRole.TEACHER:
        raise ValueError("无权操作该流程")


def get_instance(db: Session, instance_id: int) -> WorkflowInstance | None:
    return db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()


def approve(db: Session, instance: WorkflowInstance, actor: User, comment: str = "") -> WorkflowInstance:
    """通过当前节点：推进到下一节点，若已是最后一个节点则流程通过。"""
    _ensure_running(instance)
    _ensure_operator(db, instance, actor)
    defn = get_def(db, instance.def_id)
    nodes = _load_nodes(defn) if defn else []
    current = nodes[instance.current_index] if instance.current_index < len(nodes) else None

    _append_history(
        instance,
        {
            "node": current.get("key") if current else None,
            "node_name": current.get("name") if current else "未知节点",
            "actor_id": actor.id,
            "action": "approve",
            "comment": comment,
            "at": datetime.now().isoformat(),
        },
    )

    if instance.current_index + 1 >= len(nodes):
        instance.status = WorkflowStatus.APPROVED
    else:
        instance.current_index += 1
    db.commit()
    db.refresh(instance)
    return instance


def reject(db: Session, instance: WorkflowInstance, actor: User, comment: str = "") -> WorkflowInstance:
    _ensure_running(instance)
    _ensure_operator(db, instance, actor)
    defn = get_def(db, instance.def_id)
    nodes = _load_nodes(defn) if defn else []
    current = nodes[instance.current_index] if instance.current_index < len(nodes) else None

    instance.status = WorkflowStatus.REJECTED
    _append_history(
        instance,
        {
            "node": current.get("key") if current else None,
            "node_name": current.get("name") if current else "未知节点",
            "actor_id": actor.id,
            "action": "reject",
            "comment": comment,
            "at": datetime.now().isoformat(),
        },
    )
    db.commit()
    db.refresh(instance)
    return instance


def cancel(db: Session, instance: WorkflowInstance, actor: User, comment: str = "") -> WorkflowInstance:
    """撤销：仅发起人或管理员可撤销，且仅运行中可撤销。"""
    _ensure_running(instance)
    if actor.role != UserRole.ADMIN and actor.id != instance.initiator_id:
        raise ValueError("仅发起人或管理员可撤销该流程")

    instance.status = WorkflowStatus.CANCELLED
    _append_history(
        instance,
        {
            "node": None,
            "node_name": "撤销",
            "actor_id": actor.id,
            "action": "cancel",
            "comment": comment,
            "at": datetime.now().isoformat(),
        },
    )
    db.commit()
    db.refresh(instance)
    return instance


def list_instances(
    db: Session,
    *,
    initiator_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    query = db.query(WorkflowInstance)
    if initiator_id is not None:
        query = query.filter(WorkflowInstance.initiator_id == initiator_id)
    if status:
        try:
            query = query.filter(WorkflowInstance.status == WorkflowStatus(status))
        except ValueError:
            return []

    rows = query.order_by(WorkflowInstance.id.desc()).limit(limit).all()
    defs = {d.id: d for d in db.query(WorkflowDef).all()}
    return [_serialize(r, defs.get(r.def_id)) for r in rows]


def serialize_instance(db: Session, instance: WorkflowInstance) -> dict:
    return _serialize(instance, get_def(db, instance.def_id))
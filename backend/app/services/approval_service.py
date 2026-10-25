"""统一审批门面的业务层：聚合查询与统计口径的唯一入口。

`api/approval.py` 只做鉴权与响应组装，实体查询、可见性收敛、统计口径全部收敛在本服务，
避免统计口径在多处漂移（例如「受理」与「待处理」混用）。
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.leave import LeaveRequest, LeaveStatus
from app.models.material import MaterialArchive, MaterialStatus
from app.models.service import ServiceTicket, TicketStatus
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# 三类申请统一对外暴露的状态（与 api 层的 STATUS_ACTIVE 保持一致）
STATUS_ACTIVE = ("pending", "approved", "rejected")


def scoped_student_ids(db: Session, user: User) -> list[int] | None:
    """教师返回所带学生 id 列表，管理员返回 None（表示不限制）。"""
    if user.role == UserRole.ADMIN:
        return None
    ids = [s.id for s in db.query(User).filter(User.tutor_id == user.id).all()]
    return ids or []


def _naive(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def stats(
    db: Session,
    user: User,
    *,
    days: int = 30,
    student_id: int | None = None,
) -> dict:
    """审批数据统计：总量/待处理/通过/驳回 + 近 N 天口径 + 按类型分布 + 趋势。

    与旧实现的兼容性：原有 total/pending/approved/rejected/by_kind/trend 字段含义不变；
    新增 submitted / accepted / approved_window / rejected_window 四项，专供「流程条」使用，
    其口径为「近 N 天」，修正了旧实现中「文案写近 30 天、数字却是全量」的口径不符问题。
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)

    def _rows(model, fk_column, ids):
        q = db.query(model)
        if ids is not None:
            q = q.filter(fk_column.in_(ids))
        return q.all()

    ids = scoped_student_ids(db, user)
    if student_id is not None:
        ids = [student_id] if (ids is None or student_id in ids) else []
    # 办事工单的待审队列是全教师共享的（先到先审），统计口径必须与队列一致：
    # 否则导师从共享队列里通过/驳回了工单，统计数字却不动，看起来像统计坏了。
    ticket_ids = None if (student_id is None and ids is not None) else ids
    leaves = _rows(LeaveRequest, LeaveRequest.student_id, ids)
    tickets = _rows(ServiceTicket, ServiceTicket.applicant_id, ticket_ids)
    materials = _rows(MaterialArchive, MaterialArchive.student_id, ids)

    def _status(r):
        return r.status.value if hasattr(r.status, "value") else str(r.status)

    counts = {"leave": {s: 0 for s in STATUS_ACTIVE}, "ticket": {s: 0 for s in STATUS_ACTIVE}, "material": {s: 0 for s in STATUS_ACTIVE}}
    for r in leaves:
        counts["leave"][_status(r) if _status(r) in STATUS_ACTIVE else "pending"] += 1
    for r in tickets:
        counts["ticket"][_status(r) if _status(r) in STATUS_ACTIVE else "pending"] += 1
    for r in materials:
        counts["material"][_status(r) if _status(r) in STATUS_ACTIVE else "pending"] += 1

    by_kind = {k: sum(v.values()) for k, v in counts.items()}
    total = sum(by_kind.values())
    pending_total = counts["leave"]["pending"] + counts["ticket"]["pending"] + counts["material"]["pending"]
    approved_total = counts["leave"]["approved"] + counts["ticket"]["approved"] + counts["material"]["approved"]
    rejected_total = counts["leave"]["rejected"] + counts["ticket"]["rejected"] + counts["material"]["rejected"]

    # 近 N 天口径（提交 / 归档）与「已受理」（工单处理中）
    rows = list(leaves) + list(tickets) + list(materials)
    submitted = sum(1 for r in rows if (_naive(r.created_at) or since) >= since)
    approved_window = sum(
        1 for r in rows if _status(r) == "approved" and (_naive(r.created_at) or since) >= since
    )
    rejected_window = sum(
        1 for r in rows if _status(r) == "rejected" and (_naive(r.created_at) or since) >= since
    )
    accepted = sum(1 for t in tickets if t.status == TicketStatus.PROCESSING)

    # 近 N 天趋势（按天统计提交量）
    trend: dict[str, int] = defaultdict(int)
    for r in rows:
        d = _naive(r.created_at)
        if d and d >= since:
            trend[d.strftime("%m-%d")] += 1
    trend_list = [
        {
            "day": (since + timedelta(days=i)).strftime("%m-%d"),
            "count": trend[(since + timedelta(days=i)).strftime("%m-%d")],
        }
        for i in range(days)
    ]

    return {
        "total": total,
        "pending": pending_total,
        "approved": approved_total,
        "rejected": rejected_total,
        "submitted": submitted,
        "accepted": accepted,
        "approved_window": approved_window,
        "rejected_window": rejected_window,
        "by_kind": {
            "leave": {"label": "请假申请", "count": by_kind["leave"], "pending": counts["leave"]["pending"]},
            "ticket": {"label": "办事工单", "count": by_kind["ticket"], "pending": counts["ticket"]["pending"]},
            "material": {"label": "材料档案", "count": by_kind["material"], "pending": counts["material"]["pending"]},
        },
        "trend": trend_list,
    }
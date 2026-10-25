"""勋章体系持久化：只存「已获得」的结果。

勋章定义（名称/图标/阈值/受众）是产品语义，收敛在 services/badge_service.py 的常量目录里，
本表仅记录「谁在什么时候获得了哪枚勋章」以及「获得动画是否已播放」，避免规则变更时需要改数据。
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_code", name="uq_user_badge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    # 对应 badge_service.BADGE_CATALOG 中的 code
    badge_code: Mapped[str] = mapped_column(String(50), index=True)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    # 是否已播放过「获得勋章」奖励动画：未播放的会在下次进入前端时补播
    seen: Mapped[bool] = mapped_column(Boolean, default=False, comment="获得动画是否已播放")
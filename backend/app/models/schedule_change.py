"""排课调整申请：教师发起「调课 / 增课」，管理员（或本人）审批后落到正式课表。

为什么单独建表而不是直接改 ``courses``
------------------------------------
课表是教务口径的公共数据，教师端不能直接改。调课 / 增课本质是一次**待审批的变更意图**，
因此独立落一张申请单，审批通过后才由 ``services/schedule_change_service.py`` 写回
``courses``——这样「申请中」「已生效」「被驳回」三种状态都有据可查，驳回也不会污染课表。

两类申请的字段差异
------------------
- **调课（swap）**：必填 ``course_id``，并把原排课快照（原星期/节次/地点/教师）一并存下，
  审批页不用回查课程就能看清「从什么改成什么」，且课程后来被改动也不会让历史申请串味。
- **增课（add）**：没有 ``course_id``，需要完整的目标排课信息（班级、课程名、教师、地点、周次）。

两者的「目标」字段是同构的（``day_of_week / start_period / end_period / location / ...``），
所以审批与冲突检测只写一份逻辑。
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScheduleChangeKind(str, enum.Enum):
    """申请类型：调课（改已有课的时间/地点）/ 增课（新增一门课）。"""

    SWAP = "swap"
    ADD = "add"


class ScheduleChangeStatus(str, enum.Enum):
    """申请状态。

    ``cancelled`` 是申请人主动撤回——与 ``rejected`` 分开，是为了在台账里
    区分「被否掉」和「自己撤的」，前者要反思，后者不用。
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ScheduleChangeRequest(Base):
    __tablename__ = "schedule_change_requests"
    __table_args__ = (
        # 教师端「我的申请」按人 + 状态 + 时间倒序；审批队列按状态 + 时间倒序
        Index("ix_schedule_change_applicant_created", "applicant_id", "created_at"),
        Index("ix_schedule_change_status_created", "status", "created_at"),
        Index("ix_schedule_change_semester", "semester"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ScheduleChangeKind] = mapped_column(
        SAEnum(ScheduleChangeKind), index=True, comment="swap 调课 / add 增课"
    )
    status: Mapped[ScheduleChangeStatus] = mapped_column(
        SAEnum(ScheduleChangeStatus), default=ScheduleChangeStatus.PENDING, index=True
    )

    # ---- 申请人 ----
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, comment="发起申请的教师")
    applicant_name: Mapped[str] = mapped_column(String(50), default="", comment="申请人姓名快照")

    # ---- 调课专用：原排课快照（新增课程时为 None）----
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id"), default=None, index=True, comment="被调整的课程 id（增课为空）"
    )
    origin_day_of_week: Mapped[int | None] = mapped_column(Integer, default=None)
    origin_start_period: Mapped[int | None] = mapped_column(Integer, default=None)
    origin_end_period: Mapped[int | None] = mapped_column(Integer, default=None)
    origin_location: Mapped[str | None] = mapped_column(String(100), default=None)
    origin_teacher: Mapped[str | None] = mapped_column(String(50), default=None)
    origin_week_start: Mapped[int | None] = mapped_column(Integer, default=None)
    origin_week_end: Mapped[int | None] = mapped_column(Integer, default=None)
    # 申请发起时处于第几教学周：调课是「把某一周课挪走」，必须说清挪的是哪一周，
    # 否则同一天有课的多个周次无法区分。由前端按当前查看的周次带上来。
    origin_week_no: Mapped[int | None] = mapped_column(
        Integer, default=None, comment="被调整的是第几教学周（单次调课）"
    )

    # ---- 目标排课（两类共用）----
    class_group_id: Mapped[int] = mapped_column(ForeignKey("class_groups.id"), index=True)
    class_name: Mapped[str] = mapped_column(String(100), default="", comment="班级名称快照")
    course_name: Mapped[str] = mapped_column(String(100))
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), default=None, index=True, comment="目标授课教师（增课由申请人本人填）"
    )
    teacher_name: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(100), default="")
    day_of_week: Mapped[int] = mapped_column(Integer, comment="目标星期 1-7，7=周日")
    start_period: Mapped[int] = mapped_column(Integer)
    end_period: Mapped[int] = mapped_column(Integer)
    week_start: Mapped[int] = mapped_column(Integer, default=1)
    week_end: Mapped[int] = mapped_column(Integer, default=16)
    semester: Mapped[str] = mapped_column(String(20), comment="学期，如 2024-2025-1")
    credit: Mapped[float | None] = mapped_column(Float, default=None)

    # ---- 申请说明与审批留痕 ----
    # Text 列在 MySQL 下不能带字面量默认值，故 default 只写在 ORM 层、DB 层保持可空
    reason: Mapped[str | None] = mapped_column(Text, default="")
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    approver_name: Mapped[str] = mapped_column(String(50), default="")
    reject_reason: Mapped[str | None] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
    # 审批通过后实际写入的课程 id：
    # - 增课 = 新建的课程 id；
    # - 调课 = 为这一周补出来的单次调课课程 id（原课不动）。
    applied_course_id: Mapped[int | None] = mapped_column(Integer, default=None)

    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    @property
    def kind_value(self) -> str:
        return self.kind.value if hasattr(self.kind, "value") else str(self.kind)

    @property
    def status_value(self) -> str:
        return self.status.value if hasattr(self.status, "value") else str(self.status)

"""教学域：课堂考勤 / 作业 / 作业提交。

三者共同支撑教师端「我的教学」这一域，并向下游输出两类数据：

- **出勤与作业表现** → 学生画像、AI 洞察、「建议联系」候选；
- **点名与批改动作** → ``LearningEvent``（xAPI 精简版），与育人域同源。

设计要点
--------
- 考勤按「课次 + 学生」落行，而非按「课程 + 状态汇总」。原因：缺勤必须能
  追溯到具体某一天某两节课，否则「连续三次缺勤」这类规则无法计算。
- ``leave_request_id`` 记录本次缺勤已由哪条请假单核销：点名时自动比对，
  已批假的直接标 ``leave``，从数据库层保证「不会把请假的人记成旷课」。
- 作业提交用 ``UniqueConstraint(homework_id, student_id)`` 防重，重复提交走更新。
"""
import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AttendanceStatus(str, enum.Enum):
    """考勤状态。

    ``LEAVE`` 是「已批假」，与 ``ABSENT`` 严格区分——这是本模块与请假审批
    打通的关键：教师点名时不需要知道谁请过假，系统按时间窗自动判定。
    """

    PRESENT = "present"      # 出勤
    LATE = "late"            # 迟到
    ABSENT = "absent"        # 旷课
    LEAVE = "leave"          # 已批假
    EXCUSED = "excused"      # 事假 / 公假（未走系统请假，教师手工标注）


#: 计入「缺勤」的状态：统计出勤率与触发跟进任务时使用这一个集合，避免口径分散
ABSENCE_STATUSES = (AttendanceStatus.ABSENT,)


class Attendance(Base):
    """一次课次里某个学生的出勤记录。"""

    __tablename__ = "attendances"
    __table_args__ = (
        # 同一课次同一学生只允许一条：重复点名走更新，不会产生脏行
        UniqueConstraint("course_id", "attend_date", "period_start", "student_id", name="uq_attendance_seat"),
        Index("ix_attendances_course_date", "course_id", "attend_date"),
        Index("ix_attendances_student_date", "student_id", "attend_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    class_group_id: Mapped[int | None] = mapped_column(Integer, index=True, default=None)
    #: 授课教师：冗余存储，教师端统计不必再 join courses，也让历史课次在课程被删后仍可查
    teacher_id: Mapped[int | None] = mapped_column(Integer, index=True, default=None)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    attend_date: Mapped[date] = mapped_column(Date, index=True)
    period_start: Mapped[int] = mapped_column(Integer, comment="本次课起始节次")
    period_end: Mapped[int] = mapped_column(Integer, default=0, comment="本次课结束节次")
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus), default=AttendanceStatus.PRESENT, index=True
    )
    #: 由哪条请假单核销（自动比对命中时写入，便于事后追溯「为什么记的是假」）
    leave_request_id: Mapped[int | None] = mapped_column(Integer, default=None)
    remark: Mapped[str | None] = mapped_column(String(200), default=None)
    #: 是否已由本次缺勤生成跟进任务，避免同一缺勤反复建待办
    task_created: Mapped[bool] = mapped_column(Boolean, default=False)
    recorded_by: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class HomeworkStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"      # 未交
    SUBMITTED = "submitted"  # 已交待批
    GRADED = "graded"        # 已批改
    RETURNED = "returned"    # 退回重做
    LATE = "late"            # 已交但超时


class Homework(Base):
    """作业（一次布置一份）。"""

    __tablename__ = "homeworks"
    __table_args__ = (Index("ix_homeworks_course_due", "course_id", "due_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    class_group_id: Mapped[int | None] = mapped_column(Integer, index=True, default=None)
    teacher_id: Mapped[int | None] = mapped_column(Integer, index=True, default=None)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text, default=None)
    attachment_url: Mapped[str | None] = mapped_column(String(500), default=None)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    total_score: Mapped[float] = mapped_column(Float, default=100)
    status: Mapped[HomeworkStatus] = mapped_column(
        SAEnum(HomeworkStatus), default=HomeworkStatus.PUBLISHED, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class HomeworkSubmission(Base):
    """单个学生对某份作业的提交 / 批改记录。"""

    __tablename__ = "homework_submissions"
    __table_args__ = (
        UniqueConstraint("homework_id", "student_id", name="uq_homework_submission"),
        Index("ix_hw_submissions_student", "student_id", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homeworks.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus), default=SubmissionStatus.PENDING, index=True
    )
    content: Mapped[str | None] = mapped_column(Text, default=None)
    attachment_url: Mapped[str | None] = mapped_column(String(500), default=None)
    score: Mapped[float | None] = mapped_column(Float, default=None)
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    graded_by: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

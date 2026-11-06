"""排课调整申请（调课 / 增课）的请求与响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScheduleChangeCreate(BaseModel):
    """教师发起申请。

    - ``kind=swap``：必须给 ``course_id``（被调整的课），目标字段填写「改成什么样」；
    - ``kind=add``：不给 ``course_id``，目标字段即「要新增的这门课」的完整排课信息。

    服务端会做二次校验（课时占用、是否本人授课、班级是否存在于所选学期），
    这里的约束只负责挡住明显不合理的输入。
    """

    kind: str = Field("swap", description="swap 调课 / add 增课")
    course_id: int | None = Field(None, description="调课时被调整的课程 id")

    # 单次调课的两个周次：origin_week_no = 挪走哪一周，target_week = 补到哪一周
    origin_week_no: int | None = Field(None, ge=1, le=30, description="被调走的是第几教学周")
    target_week: int | None = Field(None, ge=1, le=30, description="补到第几教学周（单次）")

    class_group_id: int | None = Field(None, description="增课时必填；调课时留空则沿用原课程班级")
    course_name: str | None = Field(None, max_length=100, description="增课时必填；调课时留空则沿用原课程名")
    teacher_id: int | None = Field(None, description="目标授课教师，留空则默认申请人本人")
    location: str = Field("", max_length=100)

    day_of_week: int = Field(..., ge=1, le=7, description="目标星期，7=周日")
    start_period: int = Field(..., ge=1, le=14)
    end_period: int = Field(..., ge=1, le=14)
    week_start: int = Field(1, ge=1, le=30)
    week_end: int = Field(16, ge=1, le=30)
    semester: str | None = Field(None, max_length=20)
    credit: float | None = Field(None, ge=0, le=30)

    reason: str = Field("", max_length=2000, description="调课/增课理由")


class ScheduleChangeReview(BaseModel):
    action: str  # approve / reject
    reject_reason: str | None = None


class ScheduleChangeOut(BaseModel):
    id: int
    kind: str
    kind_label: str = ""
    status: str
    status_label: str = ""

    applicant_id: int
    applicant_name: str = ""

    course_id: int | None = None
    # 原排课（调课才有）
    origin_day_of_week: int | None = None
    origin_start_period: int | None = None
    origin_end_period: int | None = None
    origin_location: str | None = None
    origin_teacher: str | None = None
    origin_week_start: int | None = None
    origin_week_end: int | None = None
    origin_week_no: int | None = None

    class_group_id: int
    class_name: str = ""
    course_name: str = ""
    teacher_id: int | None = None
    teacher_name: str = ""
    location: str = ""
    day_of_week: int
    start_period: int
    end_period: int
    week_start: int
    week_end: int
    semester: str = ""
    credit: float | None = None

    reason: str = ""
    approver_name: str = ""
    reject_reason: str = ""
    reviewed_at: str = ""
    applied_course_id: int | None = None

    created_at: str = ""
    updated_at: str = ""
    # 服务端评估的冲突提示（仅 pending 时有意义，供审批人一眼看到风险）
    conflicts: list[str] = []

    model_config = ConfigDict(from_attributes=True)

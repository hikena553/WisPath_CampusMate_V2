from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import date, time
from typing import Optional, List, Any


class CourseOut(BaseModel):
    id: int
    name: str
    teacher: str
    teacher_id: Optional[int] = None
    location: str
    day_of_week: int
    start_period: int
    end_period: int
    week_start: int
    week_end: int
    semester: str
    credit: Optional[float] = None
    class_group_id: int
    #: 被单次调课挪走的教学周，前端渲染时跳过（原课仍在，只是这几周不上）。
    #: 对外统一暴露成 int 列表，但库里存的是 "5,7" 这种逗号分隔字符串，
    #: 所以不能靠 from_attributes 自动转换 —— 由读取端的 _course_out 手动填。
    skip_weeks: List[int] = Field(default_factory=list)
    #: 由哪张调课申请补出来的课（增课为 None）
    source_change_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("skip_weeks", mode="before")
    @classmethod
    def _parse_skip_weeks(cls, v):
        """库里的 skip_weeks 是 "5,7" 逗号分隔字符串，统一转成 int 列表。"""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x.strip().isdigit()]
        return v


class CourseCreate(BaseModel):
    class_group_id: int
    name: str
    teacher: str
    location: str
    day_of_week: int
    start_period: int
    end_period: int
    week_start: int
    week_end: int
    semester: str
    credit: Optional[float] = None
    #: 可选：显式指定授课教师账号。不填则按 teacher 姓名自动反查并回填
    teacher_id: Optional[int] = None


class CourseBatchCreate(BaseModel):
    """批量创建课程"""
    class_group_id: int
    semester: str
    courses: List[CourseCreate]


class GradeOut(BaseModel):
    id: int
    course_name: str
    score: float
    credit: float
    gpa: float
    semester: str

    model_config = ConfigDict(from_attributes=True)


class ExamOut(BaseModel):
    id: int
    course_name: str
    exam_date: date
    start_time: time
    end_time: time
    location: str

    model_config = ConfigDict(from_attributes=True)


class CourseImportRow(BaseModel):
    """导入课程的单行数据"""
    class_name: str
    course_name: str
    teacher: str
    location: str = ""
    day_of_week: int
    start_period: int
    end_period: int
    week_start: int
    week_end: int
    credit: Optional[float] = None


class CourseImportResult(BaseModel):
    """课程导入结果"""
    total: int = 0
    created: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = []
    matched_classes: list[str] = []
    unmatched_classes: list[str] = []

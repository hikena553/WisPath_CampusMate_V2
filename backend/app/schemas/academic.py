from pydantic import BaseModel, ConfigDict
from datetime import date, time
from typing import Optional, List, Any


class CourseOut(BaseModel):
    id: int
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
    class_group_id: int

    model_config = ConfigDict(from_attributes=True)


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

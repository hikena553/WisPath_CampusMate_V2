from pydantic import BaseModel, ConfigDict
from datetime import date, time
from typing import Optional, List


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

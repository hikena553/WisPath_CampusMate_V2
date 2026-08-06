from pydantic import BaseModel, ConfigDict
from datetime import date


class GrowthRecordCreate(BaseModel):
    student_id: int | None = None  # 教师和管理员可以指定学生ID
    type: str
    title: str
    description: str | None = None
    date: date
    attachment_url: str | None = None
    # 荣誉
    honor_level: str | None = None
    # 竞赛
    organizer: str | None = None
    competition_level: str | None = None
    # 实践
    practice_type: str | None = None
    practice_certificate: str | None = None
    # 论文
    paper_type: str | None = None
    paper_name: str | None = None
    first_author: str | None = None
    second_author: str | None = None
    third_author: str | None = None
    # 成果
    achievement_type: str | None = None
    achievement_name: str | None = None


class GrowthRecordOut(BaseModel):
    id: int
    student_id: int
    type: str
    title: str
    description: str | None = None
    date: date
    attachment_url: str | None = None
    # 荣誉
    honor_level: str | None = None
    # 竞赛
    organizer: str | None = None
    competition_level: str | None = None
    # 实践
    practice_type: str | None = None
    practice_certificate: str | None = None
    # 论文
    paper_type: str | None = None
    paper_name: str | None = None
    first_author: str | None = None
    second_author: str | None = None
    third_author: str | None = None
    # 成果
    achievement_type: str | None = None
    achievement_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RadarDimension(BaseModel):
    name: str
    value: float


class MonthlyStat(BaseModel):
    month: str
    count: int
    type: str


class GpaPoint(BaseModel):
    semester: str
    gpa: float


class GrowthProfileOut(BaseModel):
    total_score: float
    radar: list[RadarDimension]
    stats_by_type: list[dict]
    monthly_trend: list[MonthlyStat]
    skills: list[str]
    interests: list[str]
    total_records: int
    total_skills: int
    gpa_trend: list[GpaPoint]


class StudentProjectCreate(BaseModel):
    project_name: str
    start_date: str
    end_date: str | None = None
    is_team: bool = False
    team_members: str | None = None
    attachment_url: str | None = None


class StudentProjectOut(BaseModel):
    id: int
    student_id: int
    project_name: str
    start_date: date
    end_date: date | None = None
    is_team: bool
    team_members: str | None = None
    attachment_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

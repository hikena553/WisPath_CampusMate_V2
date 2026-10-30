import json

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
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
    # 绵小城依据成长档案生成的标签（含来源证据），供前端只读展示与溯源
    skill_items: list[dict] = []
    interest_items: list[dict] = []
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
    # 作品集扩展字段
    tech_stack: str | None = None
    my_role: str | None = None
    project_link: str | None = None
    description: str | None = None
    # 作品图片（最多 6 张，首张作封面）；传 URL 数组，落库存 JSON 字符串
    images: list[str] | None = None
    cover_url: str | None = None


class StudentProjectOut(BaseModel):
    id: int
    student_id: int
    project_name: str
    start_date: date
    end_date: date | None = None
    is_team: bool
    team_members: str | None = None
    attachment_url: str | None = None
    # 作品集扩展字段
    tech_stack: str | None = None
    my_role: str | None = None
    project_link: str | None = None
    description: str | None = None
    images: list[str] = []
    cover_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("images", "cover_url", mode="before")
    @classmethod
    def _parse_images(cls, v, info):
        """库里 images 是 JSON 字符串；cover_url 是派生字段，取第一张图。"""
        if info.field_name == "cover_url":
            return None
        if not v:
            return []
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return [str(x) for x in parsed if x] if isinstance(parsed, list) else []
            except (ValueError, TypeError):
                return []
        return v

    @model_validator(mode="after")
    def _fill_cover(self):
        if not self.cover_url and self.images:
            self.cover_url = self.images[0]
        return self

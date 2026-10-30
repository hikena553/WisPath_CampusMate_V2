from pydantic import BaseModel, ConfigDict
from datetime import date as datetime_date, datetime


class CertificateCreate(BaseModel):
    title: str
    competition_name: str | None = None
    award_level: str | None = None
    date: str | None = None
    description: str | None = None
    image_url: str | None = None


class CertificateOut(BaseModel):
    id: int
    student_id: int
    title: str
    competition_name: str | None = None
    award_level: str | None = None
    date: datetime_date | None = None
    description: str | None = None
    image_url: str | None = None
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ResumeCreate(BaseModel):
    filename: str
    url: str
    file_size: int | None = None


class ResumeOut(BaseModel):
    id: int
    filename: str
    url: str
    file_size: int | None = None
    is_current: int = 1
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# ==================== 简历导出 ====================

class ResumeTarget(BaseModel):
    """目标投递信息：岗位/行业是必答项，其余可空。

    job_key='custom' 表示用户手动输入的岗位，名称放在 custom_job 里——
    库里的岗位知识库覆盖不了所有方向，不能逼用户只能从列表里挑。
    """
    job_key: str | None = None
    industry: str | None = None
    custom_job: str | None = None
    job_type: str = ""
    city: str = ""


class ResumeMatchIn(ResumeTarget):
    pass


class ResumeDim(BaseModel):
    key: str
    label: str
    score: float
    weight: float
    note: str


class ResumeSuggest(BaseModel):
    job_key: str
    label: str
    score: float
    why: str


class ResumeMatchOut(BaseModel):
    job: dict
    score: float
    level: str
    dims: list[ResumeDim]
    hits: list[str] = []
    gaps: list[str] = []
    suggest: list[ResumeSuggest] = []
    tips: list[str] = []


class ResumeGenerateIn(ResumeTarget):
    template_key: str = "classic"
    fmt: str = "docx"          # docx | pdf
    objective: str | None = None
    save: bool = True          # 是否同时存进「我的简历」列表
    photo_url: str | None = None   # 证件照（与头像无关，仅用于简历抬头）

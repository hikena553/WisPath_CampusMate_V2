"""匿名问卷互评的请求 / 响应模型。"""
from pydantic import BaseModel, Field


class SurveyQuestion(BaseModel):
    key: str
    label: str
    max: int = 5


class PeerSurveyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    target_type: str = "peer"
    period: str | None = None
    questions: list[SurveyQuestion] = []
    status: str = "draft"


class PeerSurveyStatusUpdate(BaseModel):
    status: str


class PeerSurveyOut(BaseModel):
    id: int
    title: str
    target_type: str
    period: str | None = None
    questions: list[SurveyQuestion] = []
    status: str
    created_by: int
    created_at: str
    response_count: int = 0
    my_submitted: bool = False


class PeerSurveySubmit(BaseModel):
    target_teacher_id: int
    scores: dict[str, int] = {}
    suggestion: str | None = None


class QuestionStat(BaseModel):
    key: str
    label: str
    average: float | None = None
    distribution: dict[str, int] = {}
    response_count: int = 0


class PeerSurveyResult(BaseModel):
    """聚合结果：任何单条答卷都不出接口。"""

    survey_id: int
    title: str
    target_teacher_id: int | None = None
    response_count: int = 0
    min_sample: int = 5
    enough_sample: bool = False
    overall_average: float | None = None
    questions: list[QuestionStat] = []
    suggestions: list[str] = []


class PeerSurveyMineItem(PeerSurveyResult):
    """我的被评结果（含问卷元信息）。"""

    period: str | None = None
    target_type: str = "peer"
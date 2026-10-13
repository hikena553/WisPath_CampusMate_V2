from pydantic import BaseModel, field_validator

# 回答模式：normal 常规 / essence 本质回答（先给本质与根因，再给推导依据）
ANSWER_MODES = {"normal", "essence"}


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

    @field_validator("history")
    @classmethod
    def validate_history(cls, v: list[dict]) -> list[dict]:
        allowed_roles = {"user", "assistant"}
        sanitized = []
        for h in v:
            role = h.get("role", "")
            if role not in allowed_roles:
                continue
            sanitized.append({"role": role, "content": str(h.get("content", ""))[:4000]})
        return sanitized[-10:]
    file_url: str | None = None
    conversation_id: int | None = None
    deep_think: bool = False
    answer_mode: str = "normal"
    skip_conversation: bool = False

    @field_validator("answer_mode")
    @classmethod
    def validate_answer_mode(cls, v: str) -> str:
        v = (v or "normal").strip().lower()
        return v if v in ANSWER_MODES else "normal"


class Suggestion(BaseModel):
    text: str
    link: str | None = None
    action: str | None = None


class ChatResponse(BaseModel):
    reply: str
    suggestions: list[Suggestion] = []

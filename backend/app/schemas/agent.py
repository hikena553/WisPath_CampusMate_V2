from pydantic import BaseModel, field_validator


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
    skip_conversation: bool = False


class Suggestion(BaseModel):
    text: str
    link: str | None = None
    action: str | None = None


class ChatResponse(BaseModel):
    reply: str
    suggestions: list[Suggestion] = []

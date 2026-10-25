from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserInfo(BaseModel):
    id: int
    username: str
    name: str
    role: str
    college: str | None = None
    avatar: str | None = None
    skills_json: dict[str, Any] | None = None
    gender: str | None = None
    political_status: str | None = None
    title: str | None = None
    hometown: str | None = None
    phone: str | None = None
    qq: str | None = None
    department: str | None = None
    class_name: str | None = None
    age: int | None = None
    tutor_id: int | None = None
    password_changed: bool = False
    signature: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
    # 快捷登录：账号已绑定手机号/QQ 时下发长期凭证，供本设备一键登录
    quick_token: str | None = None
    quick_channels: list[str] = []


class QuickLoginRequest(BaseModel):
    quick_token: str
    # 本次尝试的通道：phone / qq（用于在认证失败时给出准确的提示）
    channel: str | None = None


class QuickCredentialOut(BaseModel):
    quick_token: str | None = None
    quick_channels: list[str] = []


class ProfileUpdate(BaseModel):
    avatar: str | None = None
    gender: str | None = None
    political_status: str | None = None
    title: str | None = None
    hometown: str | None = None
    phone: str | None = None
    qq: str | None = None
    department: str | None = None
    class_name: str | None = None
    age: int | None = None
    signature: str | None = None


class SkillsUpdate(BaseModel):
    skills: list[str] = []
    interests: list[str] = []


class ForgotPasswordRequest(BaseModel):
    """忘记密码：学号/工号 + 姓名 + 验证码 + 已绑定手机号或 QQ 进行身份核验。"""

    username: str
    name: str
    contact: str
    reason: str | None = None
    captcha_id: str
    captcha: str


class ForgotPasswordStatusOut(BaseModel):
    id: int
    status: str
    submitted_at: datetime
    eta_hours: int
    message: str

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    captcha_id: str
    captcha_code: str


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
    # QQ 互联授权绑定状态（openid 不对外暴露，仅返回是否已绑定与昵称）
    qq_bound: bool = False
    qq_nickname: str | None = None
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


class SmsCodeRequest(BaseModel):
    """发送短信验证码：purpose=login（未登录登录用） / bind（已登录换绑用）。"""

    phone: str
    purpose: str = "login"


class PhoneLoginRequest(BaseModel):
    phone: str
    code: str


class PhoneBindRequest(BaseModel):
    phone: str
    code: str


class QqExchangeRequest(BaseModel):
    ticket: str


class QqMobileTokenRequest(BaseModel):
    """QQ 互联移动端（Android SDK）直通授权：客户端上报 SDK 拿到的凭证。"""

    access_token: str
    openid: str


class QqMobileAuthorizeOut(BaseModel):
    """mobile/authorize 响应：已绑定 → login 分支直接登录；未绑定 → 注册票据引导补全信息。"""

    status: str  # "login" | "unregistered"
    login: LoginResponse | None = None
    register_ticket: str | None = None
    nickname: str | None = None


class RegisterSmsRequest(BaseModel):
    """注册场景发送短信：先过图形验证码，再下发短信验证码。"""

    phone: str
    captcha_id: str
    captcha_code: str


class RegisterPhoneVerifyRequest(BaseModel):
    phone: str
    code: str


class RegisterRequest(BaseModel):
    """自助注册：先选身份（学生 / 教师），账号以学号或工号为唯一标识。

    学生需补全学院、专业、导师；教师仅需学院，专业与导师可为空。
    """

    role: str = "student"
    student_no: str
    password: str
    name: str
    college_id: int = 0
    major_id: int = 0
    tutor_id: int = 0
    phone: str | None = None
    qq: str | None = None
    phone_ticket: str | None = None
    qq_ticket: str | None = None
    # 未走短信/QQ 验证通道时（资质申请期间），提交注册需图形验证码防刷
    captcha_id: str = ""
    captcha_code: str = ""


class QqAuthorizeOut(BaseModel):
    url: str


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

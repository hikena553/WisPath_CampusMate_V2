"""家校沟通的请求 / 响应模型（手机号一律脱敏输出）。"""
from pydantic import BaseModel, Field


# ── 联系人 ────────────────────────────────────────────────────


class GuardianCreate(BaseModel):
    student_id: int
    name: str = Field(min_length=1, max_length=50)
    relation: str = Field(default="家长", max_length=20)
    phone: str | None = Field(default=None, max_length=20)
    is_primary: bool = False
    remark: str | None = Field(default=None, max_length=200)


class GuardianUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    relation: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=20)
    is_primary: bool | None = None
    remark: str | None = Field(default=None, max_length=200)


class GuardianOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    name: str
    relation: str
    phone_masked: str = ""
    is_primary: bool = False
    remark: str | None = None
    created_at: str = ""


# ── 沟通台账 ──────────────────────────────────────────────────


class ContactLogCreate(BaseModel):
    student_id: int
    guardian_id: int | None = None
    scene: str = "other"
    channel: str = "note"
    content_summary: str = Field(min_length=1)
    # 选择短信通道时是否真实发送（未配置服务商则优雅降级为 pending）
    send_sms: bool = False


class ContactLogOut(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    guardian_id: int | None = None
    guardian_name: str = ""
    teacher_id: int
    scene: str
    channel: str
    status: str
    content_summary: str
    created_at: str = ""


# ── 只读分享链接 ──────────────────────────────────────────────


class ShareLinkOut(BaseModel):
    id: int
    log_id: int
    token: str
    path: str = ""
    expires_at: str = ""
    revoked: bool = False
    view_count: int = 0
    last_viewed_at: str | None = None


class SharedLogView(BaseModel):
    """家长只读页展示内容（不含学生隐私字段与内部备注）。"""

    scene: str
    scene_label: str = ""
    content_summary: str
    teacher_name: str = ""
    created_at: str = ""
    expires_at: str = ""
"""系统设置业务层：对外暴露「公开展示类」设置的读取，供登录页与各端同步站点品牌。

背景：管理端在「系统设置」中修改站点名称 / Logo / 吉祥物 / 系统公告 / 助手称谓后，
教师端、学生端与登录页需要同步生效。原 `/api/settings` 仅管理员可读，导致非管理员端
无法获取这些展示信息。此处以白名单方式提供公开读取能力，敏感配置（API Key 等）
绝不进入白名单，保证不越权泄露。
"""
from sqlalchemy.orm import Session

from app.models.setting import SystemSetting

# 公开展示类设置键（免登录可读）：站点名称 / Logo / 吉祥物 / 系统公告 / 助手称谓
PUBLIC_SETTING_KEYS: tuple[str, ...] = (
    "site_name",
    "site_logo",
    "site_mascot",
    "site_announcement",
    "agent_name",
)


def get_public_settings(db: Session) -> dict[str, str]:
    """读取公开展示类设置，未配置的键返回空字符串（返回结构稳定，便于前端统一处理）。"""
    rows = (
        db.query(SystemSetting)
        .filter(SystemSetting.key.in_(PUBLIC_SETTING_KEYS))
        .all()
    )
    stored = {row.key: (row.value or "") for row in rows}
    return {key: stored.get(key, "") for key in PUBLIC_SETTING_KEYS}
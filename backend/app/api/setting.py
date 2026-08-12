from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db
from app.core.deps import require_role
from app.core.crypto import (
    is_sensitive_key, encrypt_value, decrypt_value,
    is_encrypted, is_masked_value,
)
from app.models.user import User, UserRole
from app.models.setting import SystemSetting

router = APIRouter(prefix="/api/settings", tags=["系统设置"])


# ===== Schemas =====
class SettingOut(BaseModel):
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SettingUpdate(BaseModel):
    value: str


class SettingBatchUpdate(BaseModel):
    settings: dict  # {key: value}


# ===== Endpoints =====
@router.get("", response_model=List[SettingOut])
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """获取所有系统设置（仅管理员）"""
    settings = db.query(SystemSetting).all()
    result = []
    for s in settings:
        val = s.value
        # 敏感字段脱敏：只显示首尾各 4 字符
        if is_sensitive_key(s.key) and val and not is_masked_value(val):
            decrypted = decrypt_value(val) if is_encrypted(val) else val
            if len(decrypted) > 8:
                val = decrypted[:4] + "****" + decrypted[-4:]
            else:
                val = "****"
        result.append(SettingOut(id=s.id, key=s.key, value=val, description=s.description))
    return result


@router.get("/{key}", response_model=SettingOut)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """获取单个设置（仅管理员）"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    val = setting.value
    if is_sensitive_key(key) and val and not is_masked_value(val):
        decrypted = decrypt_value(val) if is_encrypted(val) else val
        if len(decrypted) > 8:
            val = decrypted[:4] + "****" + decrypted[-4:]
        else:
            val = "****"
    return SettingOut(id=setting.id, key=setting.key, value=val, description=setting.description)


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    data: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """更新设置（仅管理员）"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

    value = data.value
    # 敏感字段：掩码值跳过（管理员未修改），明文值加密后存储
    if is_sensitive_key(key):
        if is_masked_value(value):
            # 管理员没有修改，原样返回现有值
            if setting:
                return SettingOut(id=setting.id, key=setting.key, value=value, description=setting.description)
            return SettingOut(id=0, key=key, value=value)
        if value:  # 非空明文 → 加密
            value = encrypt_value(value)

    if not setting:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value

    db.commit()
    db.refresh(setting)

    # 返回时脱敏
    display_val = setting.value
    if is_sensitive_key(key) and display_val:
        decrypted = decrypt_value(display_val) if is_encrypted(display_val) else display_val
        if len(decrypted) > 8:
            display_val = decrypted[:4] + "****" + decrypted[-4:]
        else:
            display_val = "****"

    return SettingOut(id=setting.id, key=setting.key, value=display_val, description=setting.description)


@router.put("", response_model=dict)
def batch_update_settings(
    data: SettingBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """批量更新设置（仅管理员）"""
    updated = []
    for key, value in data.settings.items():
        # 敏感字段：掩码值跳过
        if is_sensitive_key(key) and is_masked_value(value):
            continue

        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

        # 敏感字段非空值加密
        if is_sensitive_key(key) and value:
            value = encrypt_value(value)

        if not setting:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
        updated.append(key)

    db.commit()
    return {"message": f"已更新 {len(updated)} 项设置", "updated": updated}

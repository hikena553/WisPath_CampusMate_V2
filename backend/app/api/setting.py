from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.core.database import get_db
from app.core.deps import get_current_user
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
    current_user: User = Depends(get_current_user)
):
    """获取所有系统设置"""
    settings = db.query(SystemSetting).all()
    return [SettingOut(
        id=s.id,
        key=s.key,
        value=s.value,
        description=s.description
    ) for s in settings]


@router.get("/{key}", response_model=SettingOut)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个设置"""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")
    return SettingOut(
        id=setting.id,
        key=setting.key,
        value=setting.value,
        description=setting.description
    )


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    data: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新设置（仅管理员）"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可修改设置")
    
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        setting = SystemSetting(key=key, value=data.value)
        db.add(setting)
    else:
        setting.value = data.value
    
    db.commit()
    db.refresh(setting)
    
    return SettingOut(
        id=setting.id,
        key=setting.key,
        value=setting.value,
        description=setting.description
    )


@router.put("", response_model=dict)
def batch_update_settings(
    data: SettingBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量更新设置（仅管理员）"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可修改设置")
    
    updated = []
    for key, value in data.settings.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not setting:
            setting = SystemSetting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
        updated.append(key)
    
    db.commit()
    return {"message": f"已更新 {len(updated)} 项设置", "updated": updated}

"""admin 子包共享模块：通用分页响应模型 + 系统设置读写辅助函数。"""
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.setting import SystemSetting


class PaginatedResponse(BaseModel):
    """通用分页响应模型"""
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


def _xqe_get(db: Session, key: str, default=None):
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return s.value if s and s.value not in (None, "") else default


def _xqe_set(db: Session, key: str, value: str) -> None:
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if s:
        s.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
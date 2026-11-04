"""「我的育人成长」API：教师端唯一一页以教师为第一人称的入口。

只有三个端点，因为这三件事是同一页的三个区块，不需要拆更多：

- ``GET /api/teacher/me/growth``：履职画像 + 成长轨迹 + 影响力曲线 + 能力雷达；
- ``GET /api/teacher/me/capabilities``：只取雷达（AI 与移动端小块展示时用）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.services.teacher_growth_service import CAPABILITIES, build_my_growth

router = APIRouter(prefix="/api/teacher/me", tags=["teacher-me"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


@router.get("/growth")
def my_growth(teacher: User = Depends(_teacher_only), db: Session = Depends(get_db)):
    """我的育人成长全量数据。"""
    return build_my_growth(db, teacher)


@router.get("/capabilities")
def my_capabilities(teacher: User = Depends(_teacher_only), db: Session = Depends(get_db)):
    """九项职业能力雷达（轻量版）。"""
    data = build_my_growth(db, teacher)
    return {"radar": data["radar"], "level": data["level"], "dimensions": CAPABILITIES}

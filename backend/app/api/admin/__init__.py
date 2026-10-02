"""管理端 API 子包：由 app/api/admin.py 按域拆分而来（p4_2）。

按域拆分为 knowledge / users / courses / xique / dashboard 五个子 router，
共享的 PaginatedResponse 与系统设置读写辅助（_xqe_get/_xqe_set）位于 common.py。
聚合 router 保留 /api/admin 前缀与全部路由路径、响应结构不变。
"""
from fastapi import APIRouter

from app.api.admin.knowledge import router as _knowledge_router
from app.api.admin.users import router as _users_router
from app.api.admin.courses import router as _courses_router
from app.api.admin.xique import router as _xique_router
from app.api.admin.dashboard import router as _dashboard_router

# 聚合路由：前缀只在这里声明一次；子 router 按原 admin.py 的顺序 include
router = APIRouter(prefix="/api/admin", tags=["admin"])
router.include_router(_knowledge_router)
router.include_router(_users_router)
router.include_router(_courses_router)
router.include_router(_xique_router)
router.include_router(_dashboard_router)

__all__ = ["router"]
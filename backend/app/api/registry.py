"""统一路由注册表：全部 API Router 在此登记，main.py 只负责组装应用。"""
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.agent import router as agent_router
from app.api.campus import router as campus_router
from app.api.growth import router as growth_router
from app.api.academic import router as academic_router
from app.api.service import router as service_router
from app.api.leave import router as leave_router
from app.api.crisis import router as crisis_router
from app.api.teacher import router as teacher_router
from app.api.upload import router as upload_router
from app.api.conversations import router as conversations_router
from app.api.messages import router as messages_router
from app.api.groups import router as groups_router
from app.api.announcement import router as announcement_router
from app.api.admin import router as admin_router
from app.api.knowledge import router as knowledge_router
from app.api.organization import router as organization_router
from app.api.notification import router as notification_router
from app.api.feedback import router as feedback_router
from app.api.setting import router as setting_router
from app.api.grade_analysis import router as grade_analysis_router
from app.api.profile import router as profile_router
from app.api.lost_found import router as lost_found_router
from app.api.voice import router as voice_router
from app.api.plan import router as plan_router
from app.api.community import router as community_router
from app.api.portfolio import router as portfolio_router
from app.api.resources import router as resources_router
from app.api.feeds import router as feeds_router
from app.api.emotions import router as emotions_router
from app.api.approval import router as approval_router
from app.api.material import router as material_router

# 业务模块路由：按领域聚合登记，新增模块在此追加一行即可
ROUTERS = [
    auth_router,
    agent_router,
    campus_router,
    growth_router,
    academic_router,
    service_router,
    leave_router,
    crisis_router,
    teacher_router,
    conversations_router,
    upload_router,
    messages_router,
    groups_router,
    announcement_router,
    admin_router,
    knowledge_router,
    organization_router,
    notification_router,
    feedback_router,
    setting_router,
    grade_analysis_router,
    profile_router,
    lost_found_router,
    voice_router,
    plan_router,
    community_router,
    portfolio_router,
    resources_router,
    feeds_router,
    emotions_router,
    approval_router,
    material_router,
]


def include_all_routers(app: FastAPI) -> None:
    """集中注册全部业务路由。"""
    for router in ROUTERS:
        app.include_router(router)
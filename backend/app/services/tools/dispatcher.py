"""execute_tool 收口：按工具名分发到各域 handler，统一限流 + 结果脱敏。"""

from app.core.database import SessionLocal
from app.models.user import User

from .community import (
    _create_community_post,
    _query_community_posts,
    _query_portfolio,
    _query_resources,
)
from .lost_found import _create_lost_found, _search_lost_found
from .plan import (
    _query_plan_overview,
    _query_plan_stages,
    _query_profile_overview,
    _submit_plan_stage,
)
from .sanitize import _check_tool_rate_limit, _sanitize_tool_result
from .student import (
    _analyze_grades,
    _analyze_growth,
    _analyze_schedule,
    _confirm_growth_record,
    _create_growth_record,
    _create_leave,
    _query_announcements,
    _query_exams,
    _query_grades,
    _query_knowledge,
    _query_sceneries,
    _query_schedule,
    _submit_service_request,
    _update_project_stage,
)
from .teacher import (
    _analyze_leave,
    _approve_leave,
    _query_crisis_alerts,
    _query_growth_stats,
    _query_pending_leaves,
    _query_student_detail,
    _query_students,
)




async def execute_tool(name: str, args: dict, user: User, conv_id: int | None = None) -> dict:
    if not _check_tool_rate_limit(user.id):
        return {"error": "工具调用过于频繁，请稍后再试"}

    db = SessionLocal()
    try:
        handler = {
            "create_leave": _create_leave,
            "create_growth_record": _create_growth_record,
            "confirm_growth_record": _confirm_growth_record,
            "update_project_stage": lambda db, a, u: _update_project_stage(db, a, u, conv_id),
            "submit_service_request": _submit_service_request,
            "query_schedule": _query_schedule,
            "query_grades": _query_grades,
            "query_exams": _query_exams,
            "query_knowledge": _query_knowledge,
            "query_sceneries": _query_sceneries,
            "query_announcements": _query_announcements,
            "analyze_grades": _analyze_grades,
            "analyze_schedule": _analyze_schedule,
            "analyze_growth": _analyze_growth,
            # 失物招领
            "search_lost_found": _search_lost_found,
            "create_lost_found": _create_lost_found,
            # 学习计划 / 作品集 / 社区 / 资源 / 成长画像
            "query_plan_overview": _query_plan_overview,
            "query_plan_stages": _query_plan_stages,
            "submit_plan_stage": _submit_plan_stage,
            "query_portfolio": _query_portfolio,
            "query_community_posts": _query_community_posts,
            "create_community_post": _create_community_post,
            "query_resources": _query_resources,
            "query_profile_overview": _query_profile_overview,
            # 教师工具
            "query_pending_leaves": _query_pending_leaves,
            "analyze_leave": _analyze_leave,
            "query_students": _query_students,
            "query_crisis_alerts": _query_crisis_alerts,
            "approve_leave": _approve_leave,
            "query_student_detail": _query_student_detail,
            "query_growth_stats": _query_growth_stats,
        }
        fn = handler.get(name)
        if not fn:
            return {"error": f"未知工具: {name}"}
        result = fn(db, args, user)
        if hasattr(result, '__await__'):
            result = await result
        # S5:统一脱敏后返回(学号移除、危机摘要/请假原因截断、列表限条、message 限长)
        return _sanitize_tool_result(name, result)
    finally:
        db.close()

"""开源参考复用工具 handlers：检索可复用开源项目、生成页面骨架。

供绵小城智能体调用，替代"逆向搬运他人项目"的合规做法。
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.services import reference_service as svc


def _search_reference_library(db: Session, args: dict, user: User) -> dict:
    query = str(args.get("query") or "").strip()
    if not query:
        return {"success": False, "message": "请提供要查找的能力或需求关键词"}
    limit = args.get("limit") or 5
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        limit = 5
    items = svc.search_references(db, query, limit=limit)
    return {
        "success": True,
        "count": len(items),
        "results": [
            {
                "name": r.name,
                "license": r.license,
                "license_category": r.license_category,
                "stars": r.stars,
                "repo_url": r.repo_url,
                "tech_tags": r.tech_tags,
                "reusable_scope": r.reusable_scope,
                "attribution": r.attribution,
            }
            for r in items
        ],
        "message": "以上为可合法复用的开源项目，请按其许可证要求保留署名。",
    }


def _generate_page_scaffold(db: Session, args: dict, user: User) -> dict:
    requirement = str(args.get("requirement") or "").strip()
    if not requirement:
        return {"success": False, "message": "请提供页面需求描述"}
    result = svc.generate_scaffold(
        db,
        requirement=requirement,
        page_name=args.get("page_name"),
    )
    return {
        "success": True,
        "page_name": result["page_name"],
        "route_path": result["route_path"],
        "attribution": result["attribution"],
        "files": result["files"],
        "notes": result["notes"],
        "message": "页面骨架已生成（本地模板生成），请按 TODO 处接入真实接口。",
    }

"""开源参考库 API：管理端维护参考项目，并提供页面脚手架生成能力。

合规设计：检索与脚手架生成对全体登录用户开放；参考库的增删改仅管理员可操作。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.reference import OpenSourceReference
from app.models.user import User, UserRole
from app.schemas.reference import (
    LICENSE_CATEGORIES,
    ReferenceCreate,
    ReferenceOut,
    ReferenceUpdate,
    ScaffoldRequest,
    ScaffoldResponse,
)
from app.services import reference_service as svc

router = APIRouter(prefix="/api/references", tags=["references"])

_admin_only = require_role(UserRole.ADMIN)


def _to_out(item: OpenSourceReference) -> ReferenceOut:
    return ReferenceOut(
        id=item.id,
        name=item.name,
        repo_url=item.repo_url,
        homepage=item.homepage,
        license=item.license,
        license_category=item.license_category,
        stars=item.stars,
        language=item.language,
        tech_tags=item.tech_tags,
        summary=item.summary,
        reusable_scope=item.reusable_scope,
        attribution=item.attribution,
        is_builtin=item.is_builtin,
        enabled=item.enabled,
    )


@router.get("")
def list_references(
    search: str | None = Query(None, max_length=100),
    license_category: str | None = Query(None),
    enabled_only: bool = Query(False),
    user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    """参考库列表（管理端）：按收藏量倒序。"""
    items = svc.list_references(
        db, search=search, license_category=license_category, enabled_only=enabled_only
    )
    return {
        "items": [_to_out(i) for i in items],
        "count": len(items),
        "license_categories": svc.LICENSE_CATEGORY_LABEL,
    }


@router.get("/search")
def search_references(
    q: str = Query(..., min_length=1, max_length=200, description="需求/关键词"),
    limit: int = Query(5, ge=1, le=20),
    license_category: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按需求检索可复用的开源项目（全体登录用户）。"""
    items = svc.search_references(db, q.strip(), limit=limit, license_category=license_category)
    return {
        "results": [_to_out(i) for i in items],
        "count": len(items),
        "trace_id": f"ref-{uuid.uuid4().hex[:12]}",
    }


@router.post("/scaffold", response_model=ScaffoldResponse)
def generate_scaffold(
    req: ScaffoldRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按需求生成 Vue 页面骨架（本地模板生成，自动附出处署名）。"""
    result = svc.generate_scaffold(
        db,
        requirement=req.requirement.strip(),
        page_name=req.page_name,
        include_reference_ids=req.include_reference_ids,
    )
    result["matched_references"] = [_to_out(r) for r in result["matched_references"]]
    return result


@router.post("", response_model=ReferenceOut)
def create_reference(
    req: ReferenceCreate,
    user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    if req.license_category not in LICENSE_CATEGORIES:
        raise HTTPException(400, f"许可证分级不合法，可选：{', '.join(sorted(LICENSE_CATEGORIES))}")
    item = svc.create_reference(db, **req.model_dump())
    return _to_out(item)


@router.put("/{ref_id}", response_model=ReferenceOut)
def update_reference(
    ref_id: int,
    req: ReferenceUpdate,
    user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    data = req.model_dump(exclude_unset=True)
    if data.get("license_category") and data["license_category"] not in LICENSE_CATEGORIES:
        raise HTTPException(400, f"许可证分级不合法，可选：{', '.join(sorted(LICENSE_CATEGORIES))}")
    item = svc.update_reference(db, ref_id, **data)
    if not item:
        raise HTTPException(404, "参考项目不存在")
    return _to_out(item)


@router.delete("/{ref_id}")
def delete_reference(
    ref_id: int,
    user: User = Depends(_admin_only),
    db: Session = Depends(get_db),
):
    if not svc.delete_reference(db, ref_id):
        raise HTTPException(404, "参考项目不存在")
    return {"success": True}

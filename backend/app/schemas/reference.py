"""开源参考库的请求 / 响应模型。"""
from pydantic import BaseModel, Field

LICENSE_CATEGORIES = {"permissive", "weak-copyleft", "copyleft", "unknown"}


class ReferenceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    repo_url: str = Field(min_length=1, max_length=500)
    homepage: str | None = None
    license: str = Field(min_length=1, max_length=50)
    license_category: str = "permissive"
    stars: int = 0
    language: str | None = None
    tech_tags: str | None = None
    summary: str | None = None
    reusable_scope: str | None = None
    attribution: str | None = None
    enabled: bool = True


class ReferenceUpdate(BaseModel):
    name: str | None = None
    repo_url: str | None = None
    homepage: str | None = None
    license: str | None = None
    license_category: str | None = None
    stars: int | None = None
    language: str | None = None
    tech_tags: str | None = None
    summary: str | None = None
    reusable_scope: str | None = None
    attribution: str | None = None
    enabled: bool | None = None


class ReferenceOut(BaseModel):
    id: int
    name: str
    repo_url: str
    homepage: str | None = None
    license: str
    license_category: str
    stars: int
    language: str | None = None
    tech_tags: str | None = None
    summary: str | None = None
    reusable_scope: str | None = None
    attribution: str | None = None
    is_builtin: bool = False
    enabled: bool = True


class ScaffoldRequest(BaseModel):
    """页面脚手架生成请求。

    requirement: 需求描述，用于从参考库检索可复用项目并推断页面骨架结构。
    page_name: 可选，生成的页面组件名（PascalCase），不传则按需求推断。
    include_reference_ids: 可选，指定要引用的参考库项目 id 列表。
    """

    requirement: str = Field(min_length=2, max_length=500)
    page_name: str | None = None
    include_reference_ids: list[int] = []


class ScaffoldResponse(BaseModel):
    page_name: str
    route_path: str
    matched_references: list[ReferenceOut] = []
    attribution: str
    files: dict[str, str]
    notes: list[str] = []

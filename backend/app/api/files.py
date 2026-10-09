"""文件下载鉴权（S4）：替换原 /uploads 静态挂载，登录用户方可访问上传文件。

- `/api/files/{category}/{filename}` 新接口：分类白名单 + 真实路径前缀校验，防目录穿越；
- `/uploads/{path:path}` 旧 URL 兼容路由（同样鉴权）：数据库存量的 `/uploads/...`、
  `/uploads/announcements/...` 等地址无需迁移即可继续访问，未登录一律 404。
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.deps import get_current_user, get_optional_user
from app.models.user import User

router = APIRouter(tags=["files"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
_upload_root = UPLOAD_DIR.resolve()

# category → 相对 uploads 根的子目录（root 表示根目录本身）
CATEGORY_DIRS = {
    "root": "",
    "announcements": "announcements",
    "branding": "branding",
    "documents": "documents",
}


def resolve_safe(rel_path: str, sub_dir: str = "") -> Path | None:
    """按子目录拼接相对路径，校验真实路径仍位于 uploads 根内。

    拒绝绝对路径与 `..` 穿越；resolve() 后再做前缀校验，可拦截符号链接逃逸。
    """
    if not rel_path or rel_path.startswith(("/", "\\")):
        return None
    parts = Path(rel_path).parts
    if ".." in parts:
        return None
    base = (_upload_root / sub_dir).resolve() if sub_dir else _upload_root
    target = (base / rel_path).resolve()
    try:
        target.relative_to(_upload_root)
    except ValueError:
        return None
    return target if target.is_file() else None


@router.get("/api/files/{category}/{filename}")
def download_file(
    category: str,
    filename: str,
    user: User | None = Depends(get_optional_user),
):
    """受保护文件下载：分类白名单 + 真实路径校验。

    例外：`branding`（站点 Logo / 吉祥物）属于品牌公开素材，登录页等未登录场景
    也需要渲染，故允许匿名访问；其余分类仍强制登录。
    """
    if category not in CATEGORY_DIRS:
        raise HTTPException(404, "文件不存在")
    if category != "branding" and user is None:
        raise HTTPException(401, "未登录或登录已失效")
    path = resolve_safe(filename, CATEGORY_DIRS[category])
    if not path:
        raise HTTPException(404, "文件不存在")
    return FileResponse(path)


@router.get("/uploads/{path:path}")
def download_file_legacy(path: str, user: User = Depends(get_current_user)):
    """旧 URL 兼容（鉴权）：存量 /uploads/xxx、/uploads/announcements/xxx 等。"""
    file_path = resolve_safe(path)
    if not file_path:
        raise HTTPException(404, "文件不存在")
    return FileResponse(file_path)
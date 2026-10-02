import os
import re
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user
from app.models.user import User
from app.utils.rate_limiter import check_rate_limit

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_UPLOADS_PER_MINUTE = 20
ALLOWED_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".pdf", ".doc", ".docx", ".zip", ".rar"}
ALLOWED_MIME_PREFIXES = ("image/", "application/pdf", "application/vnd.openxmlformats-officedocument", "application/msword", "application/zip", "application/x-rar", "application/x-zip-compressed")

# 压缩包安全限制（防解压炸弹与路径穿越）
ZIP_MAX_MEMBERS = 200
ZIP_MAX_MEMBER_SIZE = 50 * 1024 * 1024  # 单成员 ≤ 50MB
ZIP_MAX_TOTAL_SIZE = 300 * 1024 * 1024  # 解压总量 ≤ 300MB


def _validate_archive(content: bytes) -> None:
    """zip 压缩包安全校验：成员数 / 单成员大小 / 总量 / 路径穿越。

    非 PK 头（如 rar）不在此校验，但 rar 同样受 magic MIME 校验约束。
    """
    if not content.startswith(b"PK"):
        return
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            infos = zf.infolist()
            if len(infos) > ZIP_MAX_MEMBERS:
                raise HTTPException(400, f"压缩包内文件数超过限制（最多 {ZIP_MAX_MEMBERS} 个）")
            total = 0
            for info in infos:
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                parts = Path(name).parts
                if name.startswith("/") or ".." in parts:
                    raise HTTPException(400, "压缩包包含非法路径，已拒绝")
                if info.file_size > ZIP_MAX_MEMBER_SIZE:
                    raise HTTPException(400, "压缩包内单个文件过大")
                total += info.file_size
                if total > ZIP_MAX_TOTAL_SIZE:
                    raise HTTPException(400, "压缩包解压后总大小超过限制")
    except zipfile.BadZipFile:
        raise HTTPException(400, "压缩包格式损坏")


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "unknown"
    # 用户级 + IP 兜底双维限流
    check_rate_limit(f"upload:user:{user.id}", MAX_UPLOADS_PER_MINUTE, 60, "上传过于频繁，请稍后再试")
    check_rate_limit(f"upload:ip:{client_ip}", MAX_UPLOADS_PER_MINUTE * 3, 60, "当前网络上传过于频繁，请稍后再试")

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if not ext or ext not in ALLOWED_TYPES:
        raise HTTPException(400, f"不支持的文件类型: {ext}")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大，最大允许 {MAX_FILE_SIZE // 1024 // 1024}MB")
    # MIME 内容嗅探为硬校验：magic 缺失时拒绝上传，不允许静默跳过
    try:
        import magic
    except ImportError:
        raise HTTPException(503, "文件校验服务不可用，请稍后重试")
    mime_type = magic.from_buffer(content[:2048], mime=True)
    if not mime_type.startswith(ALLOWED_MIME_PREFIXES):
        raise HTTPException(400, f"文件内容类型不匹配: {mime_type}")
    if ext in (".zip", ".rar") or mime_type in ("application/zip", "application/x-zip-compressed", "application/x-rar"):
        _validate_archive(content)

    safe_name = re.sub(r'[^\w.-]', '_', Path(filename).stem)[:64]
    save_name = f"{safe_name}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = UPLOAD_DIR / save_name
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)
    return JSONResponse({"url": f"/api/files/root/{save_name}", "filename": filename})
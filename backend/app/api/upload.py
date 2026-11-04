import os
import re
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Query
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user
from app.models.user import User
from app.services.file_retention import CHAT_FILE_DIR
from app.utils.rate_limiter import check_rate_limit

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
# 聊天里发送的文件：单文件上限 5GB，落盘 chat_files，由周期任务保留 7 天后删除
CHAT_FILE_MAX_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
MAX_UPLOADS_PER_MINUTE = 20
ALLOWED_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".zip", ".rar",
                 # 语音消息（聊天「按住说话」录制的音频）
                 ".webm", ".m4a", ".mp3", ".wav", ".ogg", ".opus", ".aac", ".amr"}
ALLOWED_MIME_PREFIXES = (
    "image/", "audio/", "video/webm",
    "application/pdf", "application/vnd.openxmlformats-officedocument",
    "application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
    "text/plain", "application/zip", "application/x-rar", "application/x-zip-compressed",
)
# Safari 的 MediaRecorder 只出 mp4 容器（audio/mp4），libmagic 对 ISO BMFF 常判成
# video/mp4；只对 m4a 这个扩展名放行这两个 MIME，别的一律按原规则拒绝。
AUDIO_CONTAINER_EXTS = (".m4a",)
AUDIO_CONTAINER_MIMES = ("audio/mp4", "video/mp4")

# 聊天文件额外放行视频与常见压缩格式（5GB 的文件多为视频/资料包）
CHAT_ALLOWED_TYPES = ALLOWED_TYPES | {
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".m4v",
    ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz",
    ".csv", ".md", ".json", ".xml",
}
CHAT_ALLOWED_MIME_PREFIXES = ALLOWED_MIME_PREFIXES + (
    "video/",
    "application/x-7z-compressed", "application/x-tar", "application/gzip",
    "application/x-gzip", "application/x-bzip2", "application/x-xz",
    "application/x-compressed-tar", "application/json", "application/xml",
)

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
    mime_ok = mime_type.startswith(ALLOWED_MIME_PREFIXES) or (
        ext in AUDIO_CONTAINER_EXTS and mime_type in AUDIO_CONTAINER_MIMES
    )
    if not mime_ok:
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


def _check_chat_file_mime(head: bytes) -> None:
    """聊天文件内容嗅探：只读文件头，避免把 5GB 内容读进内存。"""
    try:
        import magic
    except ImportError:
        raise HTTPException(503, "文件校验服务不可用，请稍后重试")
    mime_type = magic.from_buffer(head, mime=True)
    if not mime_type.startswith(CHAT_ALLOWED_MIME_PREFIXES):
        raise HTTPException(400, f"文件内容类型不匹配: {mime_type}")


@router.post("/upload/chat-file")
async def upload_chat_file(
    request: Request,
    filename: str = Query(..., max_length=255),
    user: User = Depends(get_current_user),
):
    """聊天文件上传（裸 body 流式落盘）：单文件 ≤ 5GB，保存到 chat_files，7 天后自动清理。

    与 `/api/upload` 的 multipart 不同，这里直接消费请求流，5GB 文件不会在内存 /
    临时目录里多留一份副本；文件名通过 query 传入，认证走 Authorization 头。
    """
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"upload:user:{user.id}", MAX_UPLOADS_PER_MINUTE, 60, "上传过于频繁，请稍后再试")
    check_rate_limit(f"upload:ip:{client_ip}", MAX_UPLOADS_PER_MINUTE * 3, 60, "当前网络上传过于频繁，请稍后再试")

    ext = Path(filename).suffix.lower()
    if not ext or ext not in CHAT_ALLOWED_TYPES:
        raise HTTPException(400, f"不支持的文件类型: {ext}")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > CHAT_FILE_MAX_SIZE:
        raise HTTPException(413, f"文件过大，单个文件最大 {CHAT_FILE_MAX_SIZE // 1024 // 1024 // 1024}GB")

    safe_name = re.sub(r'[^\w.-]', '_', Path(filename).stem)[:64]
    save_name = f"{safe_name}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = CHAT_FILE_DIR / save_name
    CHAT_FILE_DIR.mkdir(parents=True, exist_ok=True)

    size = 0
    sniffed = False
    try:
        with open(save_path, "wb") as f:
            async for chunk in request.stream():
                if not sniffed:
                    sniffed = True
                    _check_chat_file_mime(chunk[:2048])
                size += len(chunk)
                if size > CHAT_FILE_MAX_SIZE:
                    raise HTTPException(413, f"文件过大，单个文件最大 {CHAT_FILE_MAX_SIZE // 1024 // 1024 // 1024}GB")
                f.write(chunk)
        if size == 0:
            raise HTTPException(400, "文件为空")
    except Exception:
        save_path.unlink(missing_ok=True)
        raise

    return JSONResponse({"url": f"/api/files/chat/{save_name}", "filename": filename})
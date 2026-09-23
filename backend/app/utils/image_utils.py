"""图片工具：把本地上传的图片转换为多模态模型可用的 data URL。

DashScope / OpenAI 兼容接口的 image_url 需要公网可访问地址，而本项目的
上传目录是本地磁盘（/uploads/xxx.jpg），因此统一读取文件并转 base64。
"""
import base64
import io
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# backend/app/utils/image_utils.py -> backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BACKEND_ROOT / "uploads"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# 单图 base64 体积上限（DashScope 约 10MB，留出余量）
MAX_IMAGE_BYTES = 7 * 1024 * 1024


def is_image_file(url_or_name: str | None) -> bool:
    """根据扩展名判断是否为图片。"""
    if not url_or_name:
        return False
    name = url_or_name.split("?")[0].split("#")[0]
    return Path(name).suffix.lower() in IMAGE_EXTS


def resolve_upload_path(url: str) -> Path | None:
    """把 /uploads/x.jpg、http://host/uploads/x.jpg 解析为本地真实路径。

    只取文件名部分拼接上传目录，避免目录穿越。文件不存在返回 None。
    """
    if not url or url.startswith("data:"):
        return None
    candidate = url
    if "://" in candidate:
        candidate = urlparse(candidate).path
    marker = "/uploads/"
    if marker in candidate:
        candidate = candidate.split(marker, 1)[1]
    safe_name = Path(candidate.lstrip("/\\")).name
    if not safe_name:
        return None
    path = UPLOAD_DIR / safe_name
    return path if path.is_file() else None


def _shrink(raw: bytes, limit: int) -> bytes | None:
    """用 Pillow 逐步降质/降分辨率压缩到 limit 以内；Pillow 不可用则返回 None。"""
    try:
        from PIL import Image
    except ImportError:
        logger.info("Pillow 未安装，跳过图片压缩（pip install pillow 可启用大图识别）")
        return None
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        quality = 85
        for _ in range(6):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            out = buf.getvalue()
            if len(out) <= limit:
                return out
            w, h = img.size
            img = img.resize((max(1, int(w * 0.8)), max(1, int(h * 0.8))))
            quality = max(50, quality - 10)
        return None
    except Exception:
        logger.exception("图片压缩失败")
        return None


def to_data_url(url: str) -> str | None:
    """读取本地图片并编码为 data URL。失败返回 None（调用方需降级处理）。"""
    path = resolve_upload_path(url)
    if not path:
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        logger.exception("读取图片失败: %s", path)
        return None

    ext = path.suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    payload = raw
    if len(payload) > MAX_IMAGE_BYTES:
        shrunk = _shrink(raw, MAX_IMAGE_BYTES)
        if not shrunk:
            logger.warning("图片过大且无法压缩，跳过识别: %s", path.name)
            return None
        payload, mime = shrunk, "jpeg"

    return f"data:image/{mime};base64,{base64.b64encode(payload).decode()}"

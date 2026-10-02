"""品牌设计接口：AI 生成 / 上传 Logo 与吉祥物图片，供系统设置页使用。

生成能力基于阿里云百炼（DashScope）通义万相 wanx 图像生成模型：
1. 优先尝试 OpenAI 兼容端点 POST {base_url}/images/generations
2. 失败后回退 DashScope 原生异步任务端点
生成的远程图片立即下载到本地 uploads/branding 目录，保证后续访问稳定。
"""
import base64
import logging
import re
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.crypto import decrypt_value
from app.core.database import get_db
from app.core.deps import require_role
from app.models.setting import SystemSetting
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings/branding", tags=["品牌设计"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "branding"
BRANDING_URL_PREFIX = "/api/files/branding/"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

DEFAULT_IMAGE_MODEL = "wanx2.1-t2i-turbo"
DASHSCOPE_NATIVE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
DASHSCOPE_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=800, description="图片描述提示词")
    count: int = Field(4, ge=1, le=4, description="生成图片数量 1-4")
    size: str = Field("1024*1024", description="图片尺寸，如 1024*1024")


class GenerateResponse(BaseModel):
    images: list[str] = Field(default_factory=list, description="生成的本地图片 URL 列表")
    model: str = ""


# ===== 内部工具 =====
def _branding_api_key() -> str:
    """获取图像生成 API Key：优先数据库 dashscope_api_key，其次 llm_api_key，最后 .env"""
    try:
        db = get_db()
        rows = (
            db.query(SystemSetting)
            .filter(SystemSetting.key.in_(["dashscope_api_key", "llm_api_key"]))
            .all()
        )
        db.close()
        kv = {r.key: r.value for r in rows}
    except Exception:
        logger.exception("读取数据库品牌生成配置失败")
        kv = {}

    for key in ("dashscope_api_key", "llm_api_key"):
        if kv.get(key):
            decrypted = decrypt_value(kv[key])
            if decrypted:
                return decrypted
    return settings.DASHSCOPE_API_KEY or settings.llm_api_key


def _branding_base_url() -> str:
    try:
        db = get_db()
        row = (
            db.query(SystemSetting)
            .filter(SystemSetting.key == "llm_base_url")
            .first()
        )
        db.close()
        if row and row.value:
            return row.value
    except Exception:
        logger.exception("读取数据库 base_url 失败")
    return settings.LLM_BASE_URL


def _save_image_bytes(content: bytes, ext: str = ".png") -> str:
    """保存图片字节到 uploads/branding，返回本地 URL"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if ext not in ALLOWED_IMAGE_EXTS:
        ext = ".png"
    name = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / name).write_bytes(content)
    logger.info("品牌图片已保存: %s%s", BRANDING_URL_PREFIX, name)
    return f"{BRANDING_URL_PREFIX}{name}"


def _download_to_local(url: str) -> str:
    """把远程图片/DataURL 下载到本地 branding 目录"""
    if url.startswith("data:"):
        header, _, b64 = url.partition(",")
        mime = re.search(r"image/(\w+)", header)
        ext = f".{mime.group(1).lower()}" if mime else ".png"
        if ext == ".jpeg":
            ext = ".jpg"
        try:
            return _save_image_bytes(base64.b64decode(b64), ext)
        except Exception:
            logger.exception("DataURL 解码失败")
            raise HTTPException(502, "AI 返回的图片数据无法解析")
    try:
        resp = httpx.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("下载 AI 图片失败 %s: %s", url, exc)
        raise HTTPException(502, "无法下载 AI 生成的图片（临时链接可能已过期），请重试")
    content_type = resp.headers.get("content-type", "")
    mime = re.search(r"image/(\w+)", content_type)
    ext = f".{mime.group(1).lower()}" if mime else ".png"
    if ext == ".jpeg":
        ext = ".jpg"
    return _save_image_bytes(resp.content, ext)


# ===== 生成 =====
async def _generate_openai_compatible(base_url: str, api_key: str, model: str, prompt: str, count: int, size: str) -> list[str] | None:
    """OpenAI 兼容 /images/generations；失败返回 None"""
    url = base_url.rstrip("/") + "/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "n": count,
        "size": size,
        "response_format": "url",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            logger.warning("兼容模式图片生成失败 %s %s", resp.status_code, resp.text[:300])
            return None
        data = resp.json()
        urls = [item.get("url") or item.get("b64_json") for item in data.get("data", []) if item]
        return [u for u in urls if u] or None


async def _generate_dashscope_native(api_key: str, model: str, prompt: str, count: int, size: str) -> list[str] | None:
    """DashScope 原生异步任务；失败返回 None"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {"size": size, "n": count},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            DASHSCOPE_NATIVE_URL,
            headers={**headers, "X-DashScope-Async": "enable"},
            json=body,
        )
        if resp.status_code >= 400:
            logger.warning("原生模式提交失败 %s %s", resp.status_code, resp.text[:300])
            return None
        task_id = resp.json().get("output", {}).get("task_id")
        if not task_id:
            return None
        # 轮询任务结果，最长 90 秒
        import asyncio
        for _ in range(30):
            await asyncio.sleep(3)
            task_resp = await client.get(f"{DASHSCOPE_TASK_URL}/{task_id}", headers=headers)
            if task_resp.status_code >= 400:
                return None
            task = task_resp.json().get("output", {})
            status = task.get("task_status", "")
            if status == "SUCCEEDED":
                results = task.get("results", []) or []
                return [r.get("url") for r in results if r.get("url")] or None
            if status in ("FAILED", "CANCELED"):
                logger.warning("原生模式任务失败: %s", task_resp.text[:300])
                return None
    return None


@router.post("/generate", response_model=GenerateResponse)
async def generate_design_images(
    data: GenerateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """根据提示词生成 Logo / 吉祥物候选图（先兼容端点，后原生端点，均可用则取兼容结果）"""
    api_key = _branding_api_key()
    if not api_key:
        raise HTTPException(400, "未配置图像生成 API Key：请先在「AI助手设置」中填写 API Key")

    base_url = _branding_base_url()
    # 模型名可被覆盖：优先 llm_image_model 设置键,否则默认 wanx 快速版
    model = "wanx2.1-t2i-turbo"
    try:
        db = get_db()
        row = db.query(SystemSetting).filter(SystemSetting.key == "llm_image_model").first()
        db.close()
        if row and row.value and row.value.strip():
            model = row.value.strip()
    except Exception:
        logger.exception("读取图像模型配置失败")

    images: list[str] | None = None
    used_model = model
    try:
        images = await _generate_openai_compatible(base_url, api_key, model, data.prompt, data.count, data.size)
    except Exception as exc:
        logger.warning("兼容模式调用异常: %s", exc)
    if not images:
        try:
            images = await _generate_dashscope_native(api_key, model, data.prompt, data.count, data.size)
        except Exception as exc:
            logger.warning("原生模式调用异常: %s", exc)

    if not images:
        raise HTTPException(
            502,
            "图片生成失败：请检查 API Key 是否有通义万相(wanx)图像生成权限，"
            "或模型在当前服务不可用（可在设置中通过 llm_image_model 更换模型，如 wanx2.1-t2i-turbo / wanx-v1）",
        )

    local_urls = [_download_to_local(u) for u in images]
    logger.info("品牌设计生成成功: %d 张, 模型 %s", len(local_urls), used_model)
    return GenerateResponse(images=local_urls, model=used_model)


# ===== 上传 =====
@router.post("/upload")
async def upload_branding_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """上传自定义 Logo / 吉祥物图片"""
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(400, f"仅支持图片文件: {', '.join(sorted(ALLOWED_IMAGE_EXTS))}")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"图片过大，最大允许 {MAX_UPLOAD_BYTES // 1024 // 1024}MB")
    url = _save_image_bytes(content, ext)
    return {"url": url, "filename": filename}
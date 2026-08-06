import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".pdf", ".doc", ".docx", ".zip", ".rar"}
ALLOWED_MIME_PREFIXES = ("image/", "application/pdf", "application/vnd.openxmlformats-officedocument", "application/msword", "application/zip", "application/x-rar", "application/x-zip-compressed")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if not ext or ext not in ALLOWED_TYPES:
        raise HTTPException(400, f"不支持的文件类型: {ext}")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大，最大允许 {MAX_FILE_SIZE // 1024 // 1024}MB")
    try:
        import magic
        mime_type = magic.from_buffer(content[:2048], mime=True)
        if not mime_type.startswith(ALLOWED_MIME_PREFIXES):
            raise HTTPException(400, f"文件内容类型不匹配: {mime_type}")
    except ImportError:
        pass
    safe_name = re.sub(r'[^\w.-]', '_', Path(filename).stem)[:64]
    save_name = f"{safe_name}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = UPLOAD_DIR / save_name
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)
    return JSONResponse({"url": f"/uploads/{save_name}", "filename": filename})

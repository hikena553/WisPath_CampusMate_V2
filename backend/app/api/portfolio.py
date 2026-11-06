"""我的作品集 API：项目经历（复用成长档案 projects）+ 证书荣誉 + 个人简历。仅 HTTP 语义，业务下沉 services。"""
import base64
import threading
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.portfolio import (
    CertificateCreate, CertificateOut, ResumeCreate, ResumeGenerateIn, ResumeMatchIn,
    ResumeMatchOut, ResumeOut,
)
from app.services import portfolio_service, resume_export

router = APIRouter(prefix="/api/portfolio", tags=["我的作品集"])


# ==================== 证书荣誉 ====================

@router.get("/certificates", response_model=list[CertificateOut])
def list_certificates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.list_certificates(db, current_user)


@router.post("/certificates", response_model=CertificateOut)
def create_certificate(
    req: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return portfolio_service.create_certificate(db, current_user, req)


@router.put("/certificates/{cert_id}", response_model=CertificateOut)
def update_certificate(
    cert_id: int,
    req: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return portfolio_service.update_certificate(db, current_user, cert_id, req)


@router.delete("/certificates/{cert_id}")
def delete_certificate(cert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.delete_certificate(db, current_user, cert_id)


# ==================== 个人简历 ====================

@router.get("/resumes", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.list_resumes(db, current_user)


@router.post("/resumes", response_model=ResumeOut)
def create_resume(
    req: ResumeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return portfolio_service.create_resume(db, current_user, req)


@router.put("/resumes/{resume_id}/current", response_model=ResumeOut)
def set_current_resume(resume_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.set_current_resume(db, current_user, resume_id)


@router.delete("/resumes/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return portfolio_service.delete_resume(db, current_user, resume_id)

# ==================== 简历导出 ====================

def _resolve_photo_bytes(url: str | None) -> bytes | None:
    """把上传文件 URL 解析成字节（证件照渲染用）。

    上传接口落盘在 backend/uploads/ 下的子目录里，URL 形态可能是
    /uploads/x.jpg、/api/files/x.jpg 或带域名的绝对地址——统一按文件名
    在 uploads 下找，找不到就返回 None（照片缺席不该挡住导出）。
    """
    if not url:
        return None
    name = Path(url).name.strip()
    if not name:
        return None
    root = Path(__file__).resolve().parents[2] / "uploads"
    if root.exists():
        for p in root.rglob(name):
            try:
                return p.read_bytes()
            except OSError:
                continue
    return None


@router.get("/resume/options")
def resume_options():
    """导出向导第 1 步要用的选项：行业 → 岗位两级，加求职类型与模板。"""
    return {
        "industries": [
            {"key": k, "label": v["label"],
             "jobs": [{"key": j["key"], "label": j["label"]} for j in v["jobs"]]}
            for k, v in resume_export.INDUSTRIES.items()
        ],
        "job_types": resume_export.JOB_TYPE_OPTIONS,
        "templates": resume_export.TEMPLATES,
    }


# ==================== 简历模板预览缓存 ====================
# 一次真实渲染（收集档案 → 排版 → PDF → 位图）要几百毫秒，而第 3 步来回切步骤、
# 重新打开向导都会重复请求同一张缩略图。这里按「用户 + 模板 + 证件照 + 求职目标」
# 缓存渲染结果：TTL 3 分钟兜住档案编辑后的过期，LRU 上限兜住内存。
_PREVIEW_TTL = 180
_PREVIEW_MAX = 200
_preview_cache: "OrderedDict[str, tuple[float, str]]" = OrderedDict()
_preview_lock = threading.Lock()


def _preview_cache_get(key: str) -> str | None:
    now = time.time()
    with _preview_lock:
        hit = _preview_cache.get(key)
        if not hit:
            return None
        ts, image = hit
        if now - ts > _PREVIEW_TTL:
            _preview_cache.pop(key, None)
            return None
        _preview_cache.move_to_end(key)
        return image


def _preview_cache_put(key: str, image: str) -> None:
    with _preview_lock:
        _preview_cache[key] = (time.time(), image)
        _preview_cache.move_to_end(key)
        while len(_preview_cache) > _PREVIEW_MAX:
            _preview_cache.popitem(last=False)


@router.get("/resume/template-preview")
def resume_template_preview(
    template_key: str = "classic",
    photo_url: str | None = None,
    industry: str | None = None,
    job_key: str | None = None,
    custom_job: str | None = None,
    job_type: str = "",
    city: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """模板预览 = 真实渲染。

    用学生自己的档案按该模板走与导出完全相同的渲染管线（render_pdf +
    build_header/build_sections）出一页 PDF，再转成图片回给前端。
    这样第 3 步看到的缩略图就是导出效果本身——模板样式不会再和 docx/pdf
    对不上，上传的证件照也会如实出现在预览里。

    缩略图只显示在 68×93 的卡片里，按 A4 的 0.75 倍渲染已足够清晰：
    比原来的 1.6 倍少一半以上的像素，编码和传输都快得多。渲染结果按
    「用户 + 模板 + 证件照 + 求职目标」缓存 3 分钟，来回切步骤不用重算。
    """
    template = resume_export.TEMPLATE_MAP.get(template_key)
    if not template:
        raise HTTPException(404, "模板不存在")

    cache_key = "|".join((
        str(current_user.id), template_key, photo_url or "",
        industry or "", job_key or "", custom_job or "", job_type or "", city or "",
    ))
    cached = _preview_cache_get(cache_key)
    if cached:
        return {"template_key": template_key, "image": cached, "cached": True}

    try:
        import fitz  # pymupdf
    except ImportError as exc:  # 依赖没装时不抛 500，让前端能给出「直接导出」的提示
        raise HTTPException(503, "预览组件未安装，可直接导出简历") from exc

    profile = resume_export.collect_profile(db, current_user)
    target = resume_export.find_job(industry, job_key, custom_job)
    match = resume_export.evaluate(profile, industry, job_key, custom_job)
    header = resume_export.build_header(
        profile, target,
        {"match_score": match["score"], "job_type": job_type, "city": city},
    )
    sections = resume_export.build_sections(profile, target, match, template)
    try:
        pdf_bytes = resume_export.render_pdf(
            header, sections, template, photo=_resolve_photo_bytes(photo_url),
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(503, "简历渲染组件未安装，可直接导出或联系管理员") from exc
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(0.75, 0.75))
        image = "data:image/jpeg;base64," + base64.b64encode(
            pix.tobytes("jpeg", jpg_quality=85)
        ).decode("ascii")
    _preview_cache_put(cache_key, image)
    return {"template_key": template_key, "image": image}


@router.post("/resume/match", response_model=ResumeMatchOut)
def resume_match(
    req: ResumeMatchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """只算匹配度，不生成文件——向导第 2 步用它实时反馈，改岗位就重算。"""
    profile = resume_export.collect_profile(db, current_user)
    return resume_export.evaluate(profile, req.industry, req.job_key, req.custom_job)


@router.post("/resume/generate")
def resume_generate(
    req: ResumeGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成简历并直接回文件（base64）。

    不回 URL 是因为下载链接要带鉴权头，``window.open`` 发不出 Bearer；
    走 base64 让前端自己拼 Blob，手机端「保存到本地」也更稳。
    """
    if req.fmt not in ("docx", "pdf"):
        raise HTTPException(400, "只支持 docx / pdf")
    try:
        result = resume_export.generate(
            db, current_user,
            job_key=req.job_key, industry=req.industry, custom_job=req.custom_job,
            job_type=req.job_type,
            city=req.city, template_key=req.template_key, fmt=req.fmt,
            objective=req.objective,
            photo=_resolve_photo_bytes(req.photo_url),
        )
    except RuntimeError as exc:
        # 缺中文字体等环境问题：给出可执行的提示，而不是 500 空白
        raise HTTPException(503, str(exc)) from exc

    data: bytes = result["data"]
    resume_id = None
    if req.save:
        docs = Path(__file__).resolve().parents[2] / "uploads" / "documents"
        docs.mkdir(parents=True, exist_ok=True)
        stored = f"resume_{current_user.id}_{datetime.now():%Y%m%d%H%M%S}.{result['format']}"
        (docs / stored).write_bytes(data)
        row = portfolio_service.create_resume(
            db, current_user,
            ResumeCreate(filename=result["filename"],
                         url=f"/api/files/documents/{stored}",
                         file_size=len(data)),
        )
        resume_id = row.id

    return {
        "filename": result["filename"],
        "mime": result["mime"],
        "size": len(data),
        "format": result["format"],
        "match": result["match"],
        "sections": result["sections"],
        "resume_id": resume_id,
        "b64": base64.b64encode(data).decode("ascii"),
    }

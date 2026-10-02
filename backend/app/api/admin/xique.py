from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import require_role
from app.core.crypto import encrypt_value, decrypt_value, is_encrypted
from app.models.user import User, UserRole
from app.api.admin.common import _xqe_get, _xqe_set

router = APIRouter(tags=["admin"])

# ========== 喜鹊儿（青果教务）课表同步 ==========

class XiqueConfigOut(BaseModel):
    configured: bool = False
    root_url: str = ""
    username: str = ""
    password_set: bool = False
    school_year: int = 0
    term: int = 0
    semester: str = ""
    hint: str = ""


class XiqueConfigBody(BaseModel):
    root_url: str = ""
    username: str = ""
    password: str = ""  # 明文，非空时保存 md5 后加密存储
    school_year: int = 0
    term: int = 0


class XiqueSyncBody(BaseModel):
    root_url: str | None = None
    username: str | None = None
    password: str | None = None
    school_year: int | None = None
    term: int | None = None


@router.get("/courses/xique/config", response_model=XiqueConfigOut)
def xique_get_config(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """读取喜鹊儿同步配置状态（密码仅返回是否已设置）"""
    root_url = _xqe_get(db, "xqe_root_url", "")
    username = _xqe_get(db, "xqe_username", "")
    password = _xqe_get(db, "xqe_password", "")
    try:
        school_year = int(_xqe_get(db, "xqe_school_year", "0") or 0)
    except ValueError:
        school_year = 0
    try:
        term = int(_xqe_get(db, "xqe_term", "0") or 0)
    except ValueError:
        term = 0

    semester = ""
    if school_year:
        try:
            from app.services.xqe_sync import xq_to_semester
            semester = xq_to_semester(school_year, term)
        except Exception:
            semester = ""

    return XiqueConfigOut(
        configured=bool(root_url and username and password),
        root_url=root_url,
        username=username,
        password_set=bool(password),
        school_year=school_year,
        term=term,
        semester=semester,
        hint="" if root_url else "请填写教务系统根地址，如 https://jwgl.mycc.edu.cn",
    )


@router.post("/courses/xique/config", response_model=XiqueConfigOut)
def xique_save_config(
    data: XiqueConfigBody,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """保存喜鹊儿同步配置（密码保存为 md5 后加密，不落库明文）"""
    from app.services.xqe_sync import md5_hex

    root_url = data.root_url.strip().rstrip("/")
    if not root_url.startswith(("http://", "https://")):
        raise HTTPException(400, "教务地址需以 http:// 或 https:// 开头")
    _xqe_set(db, "xqe_root_url", root_url)

    username = data.username.strip()
    if username:
        _xqe_set(db, "xqe_username", username)
    else:
        raise HTTPException(400, "学号不能为空")

    if data.password:
        # 只保存 md5(明文) 的密文，用于青果二次 MD5 登录协议
        _xqe_set(db, "xqe_password", encrypt_value(md5_hex(data.password)))

    if data.school_year >= 2000:
        _xqe_set(db, "xqe_school_year", str(data.school_year))
    if data.term in (0, 1):
        _xqe_set(db, "xqe_term", str(data.term))

    db.commit()
    # 返回最新配置状态
    return xique_get_config(user=user, db=db)


@router.post("/courses/sync/xique")
def xique_sync_courses(
    data: XiqueSyncBody,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """一键同步喜鹊儿课表到本地课程表（同步请求，约 3-10 秒）"""
    from app.services.xqe_sync import (
        sync_timetable, md5_hex,
        XqeLoginError, XqeNetworkError, XqeParseError,
    )

    root_url = (data.root_url or "").strip().rstrip("/") or _xqe_get(db, "xqe_root_url", "")
    username = (data.username or "").strip() or _xqe_get(db, "xqe_username", "")
    term = data.term if data.term in (0, 1) else None
    if term is None:
        try:
            term = int(_xqe_get(db, "xqe_term", "0") or 0)
        except ValueError:
            term = 0
    school_year = data.school_year or 0
    if not school_year:
        try:
            school_year = int(_xqe_get(db, "xqe_school_year", "0") or 0)
        except ValueError:
            school_year = 0

    if not root_url:
        raise HTTPException(400, "尚未配置教务地址，请先在「喜鹊儿同步」中保存配置")
    if not username:
        raise HTTPException(400, "尚未配置学号，请先在「喜鹊儿同步」中保存配置")
    if school_year < 2000:
        raise HTTPException(400, "学年（起始年份）未配置或无效，请先保存配置")

    # 密码优先级：请求体明文 -> 存储的 md5 密文
    if data.password:
        once_md5 = md5_hex(data.password)
    else:
        stored = _xqe_get(db, "xqe_password", "")
        if not stored:
            raise HTTPException(400, "尚未配置密码，请先在「喜鹊儿同步」中保存配置")
        decrypted = decrypt_value(stored) if is_encrypted(stored) else stored
        if "****" in decrypted:
            raise HTTPException(400, "密码已脱敏未保存，请重新输入密码")
        once_md5 = decrypted

    try:
        result = sync_timetable(
            db,
            root_url=root_url,
            username=username,
            once_md5_password=once_md5,
            school_year=school_year,
            term=term,
        )
    except XqeLoginError as e:
        raise HTTPException(400, f"喜鹊儿登录失败：{e}")
    except XqeNetworkError as e:
        raise HTTPException(502, f"教务网络异常：{e}")
    except XqeParseError as e:
        raise HTTPException(502, f"课表解析失败：{e}")

    db.commit()
    return {
        "success": True,
        "message": (
            f"同步完成：学生 {result.student_name}（{result.class_name}），"
            f"学期 {result.semester}，共 {result.total} 条课程，"
            f"新增 {result.created} 条，更新 {result.updated} 条，跳过 {result.skipped} 条"
        ),
        "semester": result.semester,
        "class_name": result.class_name,
        "total": result.total,
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
    }

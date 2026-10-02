import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password, revoke_token
from app.models.user import User, UserRole
from app.schemas.user import ChangePasswordRequest, LoginRequest, LoginResponse, ProfileUpdate
from app.services.auth_service import login_user
from app.utils.rate_limiter import check_login_rate_limit

# 与 core/deps.py 保持一致
AUTH_COOKIE_NAME = "campus_token"


def _extract_token(request: Request) -> str | None:
    """从 Authorization 头或 httpOnly Cookie 中提取 token（用于幂等登出撤销）。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return request.cookies.get(AUTH_COOKIE_NAME)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)
    result = login_user(db, req.username, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # 附加 httpOnly Cookie 通道（F3）：JS 不可读，降低 XSS 窃取面；
    # 与 Bearer 双轨并存，原有前端契约不变。
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=result["access_token"],
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=(settings.ENV == "production"),
        path="/",
    )
    return result


@router.post("/logout")
def logout(request: Request, response: Response):
    """登出：撤销当前 token（幂等），并清除 httpOnly Cookie。"""
    token = _extract_token(request)
    if token:
        revoke_token(token)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return {"message": "已退出登录"}


@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    teachers = db.query(User).filter(User.role == UserRole.TEACHER).all()
    from app.schemas.user import UserInfo
    return [UserInfo.model_validate(t) for t in teachers]


@router.get("/me")
def current_identity(user: User = Depends(get_current_user)):
    """SSO 统一身份信息：校验 token 并返回当前登录者身份（学号/姓名/角色/需改密标志）。"""
    from app.schemas.user import UserInfo
    info = UserInfo.model_validate(user).model_dump()
    info["password_needs_change"] = not user.password_changed
    return info


@router.put("/profile")
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field in ("avatar", "gender", "political_status", "title", "hometown", "phone", "department", "class_name", "age"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(user, field, val)
    db.commit()
    db.refresh(user)
    from app.schemas.user import UserInfo
    return UserInfo.model_validate(user)


@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    import re
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="新密码至少 8 位")
    if not re.search(r"[A-Za-z]", data.new_password) or not re.search(r"\d", data.new_password):
        raise HTTPException(status_code=400, detail="新密码必须同时包含字母和数字")
    if data.new_password == data.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
    
    user.password_hash = hash_password(data.new_password)
    user.password_changed = True
    db.commit()
    return {"message": "密码修改成功"}
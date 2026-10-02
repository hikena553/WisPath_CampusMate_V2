from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token, is_token_revoked
from app.models.user import User, UserRole

# auto_error=False：允许同时支持 Authorization 头与 httpOnly Cookie 两种凭据通道
bearer_scheme = HTTPBearer(auto_error=False)

# httpOnly Cookie 名（登录时由 /api/auth/login 写入）
AUTH_COOKIE_NAME = "campus_token"


def _read_token(request: Request) -> str | None:
    """从 Authorization 头（优先）或 httpOnly Cookie 中提取 token。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return request.cookies.get(AUTH_COOKIE_NAME)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = None
    if credentials is not None:
        token = credentials.credentials
    if not token:
        token = _read_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已失效")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token")
    if is_token_revoked(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效 token")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    # 校验密码是否已变更（密码修改后旧 Token 失效）
    if payload.get("ph") and not user.password_hash.startswith(payload["ph"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="密码已修改，请重新登录")
    # 附带原始 token，供登出等接口撤销使用
    request.state.auth_token = token
    return user


def require_role(*roles: UserRole):
    """创建角色检查依赖"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        return current_user
    return role_checker
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, LoginResponse, ProfileUpdate
from app.services.auth_service import login_user
from app.utils.rate_limiter import check_login_rate_limit


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)
    result = login_user(db, req.username, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return result


@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    teachers = db.query(User).filter(User.role == UserRole.TEACHER).all()
    from app.schemas.user import UserInfo
    return [UserInfo.model_validate(t) for t in teachers]


@router.put("/profile")
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field in ("avatar", "gender", "political_status", "title", "hometown", "phone", "department", "class_name", "age", "tutor_id"):
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
    
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    
    user.password_hash = hash_password(data.new_password)
    user.password_changed = True
    db.commit()
    return {"message": "密码修改成功"}
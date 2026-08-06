from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token
from app.models.user import User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def login_user(db: Session, username: str, password: str) -> dict | None:
    user = authenticate_user(db, username, password)
    if not user:
        return None
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    from app.schemas.user import UserInfo
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserInfo.model_validate(user).model_dump(),
    }

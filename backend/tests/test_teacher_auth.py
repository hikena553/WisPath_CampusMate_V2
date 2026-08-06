import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.core.database import get_db
from app.api.teacher import router as teacher_router


# 模拟数据库会话
class MockDB:
    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []

    def first(self):
        return None

    def count(self):
        return 0


# 模拟用户
def mock_user(role: UserRole):
    user = User()
    user.id = 1
    user.username = "testuser"
    user.role = role
    return user


# 测试学生访问教师端API返回403
def test_student_access_denied():
    app = FastAPI()
    app.include_router(teacher_router)

    # 覆盖依赖项，返回学生用户
    def override_get_current_user():
        return mock_user(UserRole.STUDENT)

    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    response = client.get("/api/teacher/dashboard")
    assert response.status_code == 403


# 测试教师访问成功
def test_teacher_access_allowed():
    app = FastAPI()
    app.include_router(teacher_router)

    # 覆盖依赖项，返回教师用户
    def override_get_current_user():
        return mock_user(UserRole.TEACHER)

    app.dependency_overrides[get_current_user] = override_get_current_user

    # 覆盖数据库会话
    def override_get_db():
        return MockDB()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/teacher/dashboard")
    # 由于模拟数据库，可能返回200或500，但不应是403
    assert response.status_code != 403


# 测试管理员访问成功
def test_admin_access_allowed():
    app = FastAPI()
    app.include_router(teacher_router)

    # 覆盖依赖项，返回管理员用户
    def override_get_current_user():
        return mock_user(UserRole.ADMIN)

    app.dependency_overrides[get_current_user] = override_get_current_user

    # 覆盖数据库会话
    def override_get_db():
        return MockDB()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/teacher/dashboard")
    assert response.status_code != 403


# 测试require_role依赖
def test_require_role_dependency():
    # 测试角色检查函数
    def test_role(user_role: UserRole, allowed_roles: tuple[UserRole, ...], should_pass: bool):
        user = mock_user(user_role)
        role_checker = require_role(*allowed_roles)
        try:
            role_checker(user)
            if not should_pass:
                pytest.fail(f"Expected HTTPException for role {user_role}")
        except Exception as e:
            if should_pass:
                pytest.fail(f"Unexpected exception for role {user_role}: {e}")

    # 学生不应访问教师端
    test_role(UserRole.STUDENT, (UserRole.TEACHER, UserRole.ADMIN), False)
    # 教师可以访问
    test_role(UserRole.TEACHER, (UserRole.TEACHER, UserRole.ADMIN), True)
    # 管理员可以访问
    test_role(UserRole.ADMIN, (UserRole.TEACHER, UserRole.ADMIN), True)
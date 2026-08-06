import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.leave import LeaveRequest, LeaveStatus
from app.core.database import get_db
from app.api.leave import router as leave_router


# 模拟用户
def mock_user(role: UserRole, user_id: int = 1, tutor_id: int = None):
    user = User()
    user.id = user_id
    user.username = f"testuser_{user_id}"
    user.name = f"测试用户{user_id}"
    user.role = role
    user.tutor_id = tutor_id
    return user


# 模拟请假请求
def mock_leave_request(leave_id: int, student_id: int, status: LeaveStatus = LeaveStatus.PENDING):
    leave = LeaveRequest()
    leave.id = leave_id
    leave.student_id = student_id
    leave.status = status
    leave.start_date = "2024-01-01"
    leave.end_date = "2024-01-02"
    leave.reason = "测试请假"
    leave.leave_type = "事假"
    leave.created_at = MagicMock()
    leave.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    return leave


# 测试学生只能查看自己的请假申请
def test_student_can_only_view_own_leave_requests():
    app = FastAPI()
    app.include_router(leave_router)

    student = mock_user(UserRole.STUDENT, user_id=1)
    mock_db = MagicMock()
    
    # 模拟查询返回学生的请假记录
    mock_leave = mock_leave_request(1, 1)
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_leave]
    mock_db.query.return_value.filter.return_value.first.return_value = student

    def override_get_current_user():
        return student

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/leave/my")
    assert response.status_code == 200


# 测试学生不能访问教师端API（pending）
def test_student_cannot_access_pending():
    app = FastAPI()
    app.include_router(leave_router)

    student = mock_user(UserRole.STUDENT, user_id=1)
    
    def override_get_current_user():
        return student

    def override_get_db():
        return MagicMock()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/leave/pending")
    assert response.status_code == 403


# 测试学生不能访问教师端API（all）
def test_student_cannot_access_all_requests():
    app = FastAPI()
    app.include_router(leave_router)

    student = mock_user(UserRole.STUDENT, user_id=1)
    
    def override_get_current_user():
        return student

    def override_get_db():
        return MagicMock()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/leave/all")
    assert response.status_code == 403


# 测试学生不能访问教师端API（analyze）
def test_student_cannot_access_analyze():
    app = FastAPI()
    app.include_router(leave_router)

    student = mock_user(UserRole.STUDENT, user_id=1)
    
    def override_get_current_user():
        return student

    def override_get_db():
        return MagicMock()

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/leave/1/analyze")
    assert response.status_code == 403


# 测试教师只能查看自己名下学生的请假申请
def test_teacher_can_only_view_their_students_leave():
    app = FastAPI()
    app.include_router(leave_router)

    teacher = mock_user(UserRole.TEACHER, user_id=1)
    student = mock_user(UserRole.STUDENT, user_id=2, tutor_id=1)
    mock_leave = mock_leave_request(1, 2)
    
    mock_db = MagicMock()
    # 模拟查询教师名下的学生
    mock_db.query.return_value.filter.return_value.all.return_value = [student]
    # 模拟查询待审批的请假
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_leave]
    mock_db.query.return_value.filter.return_value.first.return_value = student

    def override_get_current_user():
        return teacher

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/leave/pending")
    assert response.status_code == 200


# 测试教师不能审批其他教师名下学生的请假
def test_teacher_cannot_review_other_students_leave():
    app = FastAPI()
    app.include_router(leave_router)

    teacher = mock_user(UserRole.TEACHER, user_id=1)
    other_teacher = mock_user(UserRole.TEACHER, user_id=2)
    student = mock_user(UserRole.STUDENT, user_id=3, tutor_id=2)  # 学生属于其他教师
    mock_leave = mock_leave_request(1, 3)
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_leave
    # 模拟查询学生信息
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_leave, student]

    def override_get_current_user():
        return teacher

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.post("/api/leave/1/review", json={"action": "approve"})
    assert response.status_code == 403


# 测试管理员可以查看所有请假申请
def test_admin_can_view_all_leave_requests():
    app = FastAPI()
    app.include_router(leave_router)

    admin = mock_user(UserRole.ADMIN, user_id=1)
    mock_leave = mock_leave_request(1, 2)
    student = mock_user(UserRole.STUDENT, user_id=2)
    
    mock_db = MagicMock()
    mock_db.query.return_value.order_by.return_value.all.return_value = [mock_leave]
    mock_db.query.return_value.filter.return_value.first.return_value = student

    def override_get_current_user():
        return admin

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/leave/all")
    assert response.status_code == 200


# 测试管理员可以审批任何学生的请假
def test_admin_can_review_any_leave():
    app = FastAPI()
    app.include_router(leave_router)

    admin = mock_user(UserRole.ADMIN, user_id=1)
    mock_leave = mock_leave_request(1, 2)
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_leave

    def override_get_current_user():
        return admin

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.post("/api/leave/1/review", json={"action": "approve"})
    assert response.status_code == 200


# 测试学生只能删除自己的请假申请
def test_student_can_only_delete_own_leave():
    app = FastAPI()
    app.include_router(leave_router)

    student = mock_user(UserRole.STUDENT, user_id=1)
    mock_leave = mock_leave_request(1, 1)
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_leave

    def override_get_current_user():
        return student

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.delete("/api/leave/1")
    assert response.status_code == 200


# 测试学生不能删除其他学生的请假申请
def test_student_cannot_delete_other_students_leave():
    app = FastAPI()
    app.include_router(leave_router)

    student = mock_user(UserRole.STUDENT, user_id=1)
    
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None  # 找不到记录

    def override_get_current_user():
        return student

    def override_get_db():
        return mock_db

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.delete("/api/leave/1")
    assert response.status_code == 404
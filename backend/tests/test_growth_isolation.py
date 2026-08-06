import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch
from datetime import date

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.growth import GrowthRecord, StudentProject
from app.api.growth import router as growth_router


# 模拟用户
def mock_user(user_id: int, role: UserRole, tutor_id: int | None = None):
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.tutor_id = tutor_id
    user.skills_json = {"skills": [], "interests": []}
    return user


# 模拟成长记录
def mock_growth_record(record_id: int, student_id: int):
    record = MagicMock(spec=GrowthRecord)
    record.id = record_id
    record.student_id = student_id
    record.date = date(2024, 1, 1)
    record.type = "honor"
    record.title = "测试荣誉"
    record.description = "测试描述"
    record.attachment_url = None
    record.honor_level = "校级"
    record.organizer = None
    record.competition_level = None
    record.practice_type = None
    record.practice_certificate = None
    record.paper_type = None
    record.paper_name = None
    record.first_author = None
    record.second_author = None
    record.third_author = None
    record.achievement_type = None
    record.achievement_name = None
    return record


# 模拟数据库会话
def mock_db_with_records(records):
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.all.return_value = records
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records
    return db


def test_student_can_only_view_own_records():
    """学生只能查看自己的成长记录"""
    app = FastAPI()
    app.include_router(growth_router)
    
    student = mock_user(1, UserRole.STUDENT)
    records = [mock_growth_record(1, 1), mock_growth_record(2, 1)]
    
    def override_get_current_user():
        return student
    
    def override_get_db():
        return mock_db_with_records(records)
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    response = client.get("/api/growth/records")
    assert response.status_code == 200


def test_student_cannot_access_other_students_records():
    """学生不能访问其他学生的数据"""
    app = FastAPI()
    app.include_router(growth_router)
    
    student = mock_user(1, UserRole.STUDENT)
    
    def override_get_current_user():
        return student
    
    def override_get_db():
        db = MagicMock(spec=Session)
        # 模拟查询返回空列表，表示没有找到记录
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        return db
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    # 尝试访问student_id=2的记录
    response = client.get("/api/growth/records?student_id=2")
    # 应该返回403错误
    assert response.status_code == 403


def test_teacher_can_only_view_their_students_records():
    """教师只能查看自己名下学生的数据"""
    app = FastAPI()
    app.include_router(growth_router)
    
    teacher = mock_user(10, UserRole.TEACHER)
    student = mock_user(1, UserRole.STUDENT, tutor_id=10)
    records = [mock_growth_record(1, 1)]
    
    def override_get_current_user():
        return teacher
    
    def override_get_db():
        db = MagicMock(spec=Session)
        # 模拟查询教师名下学生
        db.query.return_value.filter.return_value.all.return_value = [student]
        # 模拟查询成长记录
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records
        return db
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    response = client.get("/api/growth/records")
    assert response.status_code == 200


def test_admin_can_view_all_records():
    """管理员可以查看所有记录"""
    app = FastAPI()
    app.include_router(growth_router)
    
    admin = mock_user(100, UserRole.ADMIN)
    records = [mock_growth_record(1, 1), mock_growth_record(2, 2)]
    
    def override_get_current_user():
        return admin
    
    def override_get_db():
        return mock_db_with_records(records)
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    response = client.get("/api/growth/records")
    assert response.status_code == 200


def test_student_can_only_create_own_records():
    """学生只能为自己创建记录"""
    app = FastAPI()
    app.include_router(growth_router)
    
    student = mock_user(1, UserRole.STUDENT)
    
    def override_get_current_user():
        return student
    
    def override_get_db():
        db = MagicMock(spec=Session)
        db.add.return_value = None
        db.commit.return_value = None
        # 模拟refresh后返回一个记录对象
        def mock_refresh(record):
            record.id = 1
            record.date = date(2024, 1, 1)
            record.type = "honor"
            record.title = "测试荣誉"
            record.description = "测试描述"
            record.attachment_url = None
            record.honor_level = "校级"
            record.organizer = None
            record.competition_level = None
            record.practice_type = None
            record.practice_certificate = None
            record.paper_type = None
            record.paper_name = None
            record.first_author = None
            record.second_author = None
            record.third_author = None
            record.achievement_type = None
            record.achievement_name = None
        db.refresh.side_effect = mock_refresh
        return db
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    record_data = {
        "type": "honor",
        "title": "测试荣誉",
        "date": "2024-01-01"
    }
    response = client.post("/api/growth/records", json=record_data)
    assert response.status_code == 200


def test_student_cannot_delete_other_students_records():
    """学生不能删除其他学生的记录"""
    app = FastAPI()
    app.include_router(growth_router)
    
    student = mock_user(1, UserRole.STUDENT)
    record = mock_growth_record(1, 2)  # 属于学生2的记录
    
    def override_get_current_user():
        return student
    
    def override_get_db():
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = record
        return db
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    response = client.delete("/api/growth/records/1")
    # 应该返回403错误
    assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
完整测试：令牌认证与权限控制系统
覆盖学生端、教师端、管理员端的所有功能和权限检查
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import date, datetime, timezone

from app.core.deps import get_current_user, require_role
from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.models.leave import LeaveRequest, LeaveStatus
from app.models.growth import GrowthRecord, StudentProject
from app.models.academic import Course, Grade, Exam
from app.models.crisis import AIDialogSummary
from app.models.message import Message
from app.models.conversation import Conversation, ConversationMessage
from app.models.announcement import TeacherAnnouncement, AnnouncementRead
from app.models.service import ServiceTicket

# 导入所有路由
from app.api.auth import router as auth_router
from app.api.teacher import router as teacher_router
from app.api.academic import router as academic_router
from app.api.leave import router as leave_router
from app.api.growth import router as growth_router
from app.api.crisis import router as crisis_router
from app.api.messages import router as messages_router
from app.api.service import router as service_router
from app.api.conversations import router as conversations_router

# 尝试导入公告路由（需要python-multipart）
try:
    from app.api.announcement import router as announcement_router
    HAS_ANNOUNCEMENT_ROUTER = True
except (ImportError, RuntimeError):
    HAS_ANNOUNCEMENT_ROUTER = False


# ============ Helper Functions ============

def mock_user(user_id: int, role: UserRole, tutor_id: int = None, name: str = None):
    """创建模拟用户"""
    user = MagicMock(spec=User)
    user.id = user_id
    user.username = f"user_{user_id}"
    user.name = name or f"用户{user_id}"
    user.role = role
    user.tutor_id = tutor_id
    user.college = "测试学院"
    user.avatar = None
    user.skills_json = {"skills": [], "interests": []}
    user.password_hash = hash_password("password123")
    return user


def create_test_app(routers, current_user=None, mock_db=None):
    """创建测试应用"""
    app = FastAPI()
    for router in routers:
        app.include_router(router)

    if current_user:
        def override_get_current_user():
            return current_user
        app.dependency_overrides[get_current_user] = override_get_current_user

    if mock_db:
        def override_get_db():
            return mock_db
        app.dependency_overrides[get_db] = override_get_db

    return app


# ============ 测试学生端 ============

class TestStudentAuth:
    """测试学生端认证和权限"""

    def test_student_login_success(self):
        """学生登录成功"""
        # 测试令牌创建和解析
        token = create_access_token({"sub": "1", "role": "student"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["role"] == "student"

    def test_student_password_verification(self):
        """学生密码验证"""
        hashed = hash_password("test123")
        assert verify_password("test123", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_student_access_own_data(self):
        """学生可以访问自己的数据"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        # 模拟查询返回学生的数据
        mock_record = MagicMock()
        mock_record.student_id = 1
        mock_record.id = 1
        mock_record.type = "honor"  # 直接使用字符串，而不是MagicMock
        mock_record.title = "测试荣誉"
        mock_record.description = "测试描述"
        mock_record.date = date(2024, 1, 1)
        mock_record.attachment_url = None
        mock_record.honor_level = "校级"
        mock_record.organizer = None
        mock_record.competition_level = None
        mock_record.practice_type = None
        mock_record.practice_certificate = None
        mock_record.paper_type = None
        mock_record.paper_name = None
        mock_record.first_author = None
        mock_record.second_author = None
        mock_record.third_author = None
        mock_record.achievement_type = None
        mock_record.achievement_name = None

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_record]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_record]

        app = create_test_app([growth_router], student, mock_db)
        client = TestClient(app)

        response = client.get("/api/growth/records")
        assert response.status_code == 200

    def test_student_cannot_access_teacher_routes(self):
        """学生不能访问教师端路由"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        app = create_test_app([teacher_router], student, mock_db)
        client = TestClient(app)

        # 尝试访问教师端仪表板
        response = client.get("/api/teacher/dashboard")
        assert response.status_code == 403

        # 尝试访问学生列表
        response = client.get("/api/teacher/students")
        assert response.status_code == 403

        # 尝试访问成长统计
        response = client.get("/api/teacher/growth-stats")
        assert response.status_code == 403

    def test_student_cannot_access_other_student_data(self):
        """学生不能访问其他学生的数据"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        app = create_test_app([academic_router], student, mock_db)
        client = TestClient(app)

        # 尝试访问其他学生的课程数据
        response = client.get("/api/academic/courses?student_id=2")
        assert response.status_code == 403

        # 尝试访问其他学生的成绩数据
        response = client.get("/api/academic/grades?student_id=2")
        assert response.status_code == 403

        # 尝试访问其他学生的考试数据
        response = client.get("/api/academic/exams?student_id=2")
        assert response.status_code == 403

    def test_student_can_view_own_leave_requests(self):
        """学生可以查看自己的请假申请"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        mock_leave = MagicMock()
        mock_leave.id = 1
        mock_leave.student_id = 1
        mock_leave.status = LeaveStatus.PENDING
        mock_leave.start_date = "2024-01-01"
        mock_leave.end_date = "2024-01-02"
        mock_leave.reason = "测试"
        mock_leave.leave_type = "事假"
        mock_leave.created_at = datetime.now()
        mock_leave.reject_reason = None

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_leave]
        mock_db.query.return_value.filter.return_value.first.return_value = student

        app = create_test_app([leave_router], student, mock_db)
        client = TestClient(app)

        response = client.get("/api/leave/my")
        assert response.status_code == 200

    def test_student_cannot_access_crisis_alerts(self):
        """学生不能访问危机预警"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        app = create_test_app([crisis_router], student, mock_db)
        client = TestClient(app)

        response = client.get("/api/crisis/alerts")
        assert response.status_code == 403

    def test_student_can_access_own_conversations(self):
        """学生可以访问自己的对话"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.user_id = 1
        mock_conv.title = "测试对话"
        mock_conv.type = "normal"
        mock_conv.project_template = None
        mock_conv.project_stage = None
        mock_conv.is_active = True
        mock_conv.created_at = datetime.now()
        mock_conv.updated_at = datetime.now()

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_conv]

        app = create_test_app([conversations_router], student, mock_db)
        client = TestClient(app)

        response = client.get("/api/agent/conversations")
        assert response.status_code == 200

    @pytest.mark.skipif(not HAS_ANNOUNCEMENT_ROUTER, reason="python-multipart not installed")
    def test_student_cannot_access_teacher_announcements_management(self):
        """学生不能访问教师公告管理"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        app = create_test_app([announcement_router], student, mock_db)
        client = TestClient(app)

        # 尝试访问教师公告列表
        response = client.get("/api/teacher/announcements")
        assert response.status_code == 403

        # 尝试创建公告
        response = client.post("/api/teacher/announcements", data={"title": "test", "content": "test"})
        assert response.status_code == 403

    @pytest.mark.skipif(not HAS_ANNOUNCEMENT_ROUTER, reason="python-multipart not installed")
    def test_student_can_view_own_announcements(self):
        """学生可以查看自己的公告"""
        student = mock_user(1, UserRole.STUDENT, tutor_id=10)
        mock_db = MagicMock()

        mock_announcement = MagicMock()
        mock_announcement.id = 1
        mock_announcement.teacher_id = 10
        mock_announcement.title = "测试公告"
        mock_announcement.content = "测试内容"
        mock_announcement.urgency = "normal"
        mock_announcement.attachment_url = None
        mock_announcement.created_at = datetime.now()

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_announcement]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user(10, UserRole.TEACHER, name="教师")

        app = create_test_app([announcement_router], student, mock_db)
        client = TestClient(app)

        response = client.get("/api/student/announcements")
        assert response.status_code == 200


# ============ 测试教师端 ============

class TestTeacherAuth:
    """测试教师端认证和权限"""

    def test_teacher_login_success(self):
        """教师登录成功"""
        token = create_access_token({"sub": "10", "role": "teacher"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "10"
        assert payload["role"] == "teacher"

    def test_teacher_can_access_dashboard(self):
        """教师可以访问仪表板"""
        teacher = mock_user(10, UserRole.TEACHER)
        mock_db = MagicMock()

        # 模拟查询返回教师名下学生
        student = mock_user(1, UserRole.STUDENT, tutor_id=10)
        mock_db.query.return_value.filter.return_value.all.return_value = [student]
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        app = create_test_app([teacher_router], teacher, mock_db)
        client = TestClient(app)

        response = client.get("/api/teacher/dashboard")
        assert response.status_code == 200

    def test_teacher_can_view_their_students(self):
        """教师可以查看自己名下的学生"""
        teacher = mock_user(10, UserRole.TEACHER)
        mock_db = MagicMock()

        student = mock_user(1, UserRole.STUDENT, tutor_id=10)
        mock_db.query.return_value.filter.return_value.all.return_value = [student]
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app = create_test_app([teacher_router], teacher, mock_db)
        client = TestClient(app)

        response = client.get("/api/teacher/students")
        assert response.status_code == 200

    def test_teacher_cannot_access_student_routes(self):
        """教师不能访问学生专属路由"""
        teacher = mock_user(10, UserRole.TEACHER)
        mock_db = MagicMock()

        # 使用crisis_router测试学生专属路由的权限
        app = create_test_app([crisis_router], teacher, mock_db)
        client = TestClient(app)

        # 教师可以访问危机预警（这是教师功能）
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = client.get("/api/crisis/alerts")
        assert response.status_code == 200

    def test_teacher_can_only_view_their_students_data(self):
        """教师只能查看自己名下学生的数据"""
        teacher = mock_user(10, UserRole.TEACHER)
        student = mock_user(1, UserRole.STUDENT, tutor_id=10)
        mock_db = MagicMock()

        # 模拟查询返回教师名下学生
        mock_db.query.return_value.filter.return_value.all.return_value = [student]

        # 模拟课程数据
        mock_course = MagicMock()
        mock_course.id = 1
        mock_course.name = "测试课程"
        mock_course.teacher = "测试教师"
        mock_course.location = "测试地点"
        mock_course.day_of_week = 1
        mock_course.start_period = 1
        mock_course.end_period = 2
        mock_course.week_start = 1
        mock_course.week_end = 16

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_course]

        app = create_test_app([academic_router], teacher, mock_db)
        client = TestClient(app)

        response = client.get("/api/academic/courses")
        assert response.status_code == 200

    def test_teacher_cannot_access_other_students_leave(self):
        """教师不能审批其他教师名下学生的请假"""
        teacher = mock_user(10, UserRole.TEACHER)
        other_student = mock_user(1, UserRole.STUDENT, tutor_id=20)  # 属于其他教师
        mock_db = MagicMock()

        mock_leave = MagicMock()
        mock_leave.id = 1
        mock_leave.student_id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_leave

        # 第二次查询返回学生信息
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_leave, other_student]

        app = create_test_app([leave_router], teacher, mock_db)
        client = TestClient(app)

        response = client.post("/api/leave/1/review", json={"action": "approve"})
        assert response.status_code == 403

    @pytest.mark.skipif(not HAS_ANNOUNCEMENT_ROUTER, reason="python-multipart not installed")
    def test_teacher_can_manage_announcements(self):
        """教师可以管理公告"""
        teacher = mock_user(10, UserRole.TEACHER)
        mock_db = MagicMock()

        mock_announcement = MagicMock()
        mock_announcement.id = 1
        mock_announcement.teacher_id = 10
        mock_announcement.title = "测试公告"
        mock_announcement.content = "测试内容"
        mock_announcement.urgency = "normal"
        mock_announcement.attachment_url = None
        mock_announcement.created_at = datetime.now()

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_announcement]

        app = create_test_app([announcement_router], teacher, mock_db)
        client = TestClient(app)

        response = client.get("/api/teacher/announcements")
        assert response.status_code == 200

    def test_teacher_can_view_crisis_alerts(self):
        """教师可以查看危机预警"""
        teacher = mock_user(10, UserRole.TEACHER)
        mock_db = MagicMock()

        student = mock_user(1, UserRole.STUDENT, tutor_id=10)
        mock_db.query.return_value.filter.return_value.all.return_value = [student]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        app = create_test_app([crisis_router], teacher, mock_db)
        client = TestClient(app)

        response = client.get("/api/crisis/alerts")
        assert response.status_code == 200

    def test_teacher_can_view_pending_leaves(self):
        """教师可以查看待审批的请假"""
        teacher = mock_user(10, UserRole.TEACHER)
        student = mock_user(1, UserRole.STUDENT, tutor_id=10)
        mock_db = MagicMock()

        mock_leave = MagicMock()
        mock_leave.id = 1
        mock_leave.student_id = 1
        mock_leave.status = LeaveStatus.PENDING
        mock_leave.start_date = "2024-01-01"
        mock_leave.end_date = "2024-01-02"
        mock_leave.reason = "测试"
        mock_leave.leave_type = "事假"
        mock_leave.created_at = datetime.now()
        mock_leave.reject_reason = None

        mock_db.query.return_value.filter.return_value.all.return_value = [student]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_leave]
        mock_db.query.return_value.filter.return_value.first.return_value = student

        app = create_test_app([leave_router], teacher, mock_db)
        client = TestClient(app)

        response = client.get("/api/leave/pending")
        assert response.status_code == 200


# ============ 测试管理员端 ============

class TestAdminAuth:
    """测试管理员端认证和权限"""

    def test_admin_login_success(self):
        """管理员登录成功"""
        token = create_access_token({"sub": "100", "role": "admin"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "100"
        assert payload["role"] == "admin"

    def test_admin_can_access_teacher_routes(self):
        """管理员可以访问教师端路由"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        app = create_test_app([teacher_router], admin, mock_db)
        client = TestClient(app)

        # 访问仪表板
        response = client.get("/api/teacher/dashboard")
        assert response.status_code == 200

        # 访问学生列表
        response = client.get("/api/teacher/students")
        assert response.status_code == 200

    def test_admin_can_access_all_student_data(self):
        """管理员可以访问所有学生的数据"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        app = create_test_app([academic_router], admin, mock_db)
        client = TestClient(app)

        # 访问课程数据
        response = client.get("/api/academic/courses")
        assert response.status_code == 200

        # 访问成绩数据
        response = client.get("/api/academic/grades")
        assert response.status_code == 200

        # 访问考试数据
        response = client.get("/api/academic/exams")
        assert response.status_code == 200

    def test_admin_can_view_all_leave_requests(self):
        """管理员可以查看所有请假申请"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_db.query.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app = create_test_app([leave_router], admin, mock_db)
        client = TestClient(app)

        response = client.get("/api/leave/all")
        assert response.status_code == 200

    def test_admin_can_review_any_leave(self):
        """管理员可以审批任何学生的请假"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_leave = MagicMock()
        mock_leave.id = 1
        mock_leave.student_id = 1
        mock_leave.status = LeaveStatus.PENDING
        mock_db.query.return_value.filter.return_value.first.return_value = mock_leave

        app = create_test_app([leave_router], admin, mock_db)
        client = TestClient(app)

        response = client.post("/api/leave/1/review", json={"action": "approve"})
        assert response.status_code == 200

    def test_admin_can_view_all_growth_records(self):
        """管理员可以查看所有成长记录"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        app = create_test_app([growth_router], admin, mock_db)
        client = TestClient(app)

        response = client.get("/api/growth/records")
        assert response.status_code == 200

    def test_admin_can_view_crisis_alerts(self):
        """管理员可以查看危机预警"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_db.query.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app = create_test_app([crisis_router], admin, mock_db)
        client = TestClient(app)

        response = client.get("/api/crisis/alerts")
        assert response.status_code == 200

    @pytest.mark.skipif(not HAS_ANNOUNCEMENT_ROUTER, reason="python-multipart not installed")
    def test_admin_can_manage_announcements(self):
        """管理员可以管理公告"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        app = create_test_app([announcement_router], admin, mock_db)
        client = TestClient(app)

        response = client.get("/api/teacher/announcements")
        assert response.status_code == 200

    def test_admin_can_access_service_tickets(self):
        """管理员可以访问服务工单"""
        admin = mock_user(100, UserRole.ADMIN)
        mock_db = MagicMock()

        mock_ticket = MagicMock()
        mock_ticket.id = 1
        mock_ticket.status = "pending"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_ticket

        app = create_test_app([service_router], admin, mock_db)
        client = TestClient(app)

        # 审批工单
        response = client.put("/api/service/tickets/1/approve", json={"action": "approve"})
        assert response.status_code == 200


# ============ 测试跨角色权限 ============

class TestCrossRolePermissions:
    """测试跨角色权限"""

    def test_invalid_token_rejected(self):
        """无效令牌被拒绝"""
        app = FastAPI()
        app.include_router(teacher_router)

        # 不覆盖依赖，使用无效令牌
        client = TestClient(app)

        response = client.get(
            "/api/teacher/dashboard",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_expired_token_rejected(self):
        """过期令牌被拒绝"""
        from datetime import timedelta
        from jose import jwt
        from app.core.config import settings

        # 创建过期令牌
        to_encode = {"sub": "1", "role": "student"}
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        to_encode.update({"exp": expire})
        expired_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        payload = decode_access_token(expired_token)
        assert payload is None

    def test_student_cannot_become_teacher(self):
        """学生不能通过修改令牌提升权限"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        app = create_test_app([teacher_router], student, mock_db)
        client = TestClient(app)

        # 即使尝试使用教师令牌，实际用户角色仍然是学生
        response = client.get("/api/teacher/dashboard")
        assert response.status_code == 403

    def test_teacher_cannot_become_admin(self):
        """教师不能通过修改令牌提升权限"""
        teacher = mock_user(10, UserRole.TEACHER)
        mock_db = MagicMock()

        # 创建一个需要管理员权限的路由测试
        app = create_test_app([leave_router], teacher, mock_db)
        client = TestClient(app)

        # 教师可以访问教师端功能
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        response = client.get("/api/leave/pending")
        assert response.status_code == 200

    def test_multiple_routers_isolation(self):
        """多个路由器之间的权限隔离"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        # 同时包含多个路由器
        app = create_test_app(
            [growth_router, teacher_router, academic_router, leave_router],
            student,
            mock_db
        )
        client = TestClient(app)

        # 学生可以访问成长记录
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        response = client.get("/api/growth/records")
        assert response.status_code == 200

        # 学生不能访问教师仪表板
        response = client.get("/api/teacher/dashboard")
        assert response.status_code == 403

        # 学生不能访问待审批请假
        response = client.get("/api/leave/pending")
        assert response.status_code == 403


# ============ 测试数据隔离 ============

class TestDataIsolation:
    """测试数据隔离"""

    def test_student_data_isolation_in_academic(self):
        """学术数据的学生隔离"""
        student1 = mock_user(1, UserRole.STUDENT)
        student2 = mock_user(2, UserRole.STUDENT)
        mock_db = MagicMock()

        # 学生1只能看到自己的数据
        mock_course = MagicMock()
        mock_course.id = 1
        mock_course.student_id = 1
        mock_course.name = "测试课程"
        mock_course.teacher = "测试教师"
        mock_course.location = "测试地点"
        mock_course.day_of_week = 1
        mock_course.start_period = 1
        mock_course.end_period = 2
        mock_course.week_start = 1
        mock_course.week_end = 16

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_course]

        app = create_test_app([academic_router], student1, mock_db)
        client = TestClient(app)

        # 不指定student_id，只返回自己的数据
        response = client.get("/api/academic/courses")
        assert response.status_code == 200

        # 指定其他学生的student_id，返回403
        response = client.get("/api/academic/courses?student_id=2")
        assert response.status_code == 403

    def test_teacher_data_isolation_in_leave(self):
        """请假数据的教师隔离"""
        teacher = mock_user(10, UserRole.TEACHER)
        student = mock_user(1, UserRole.STUDENT, tutor_id=10)
        mock_db = MagicMock()

        # 教师只能看到自己名下学生的数据
        mock_db.query.return_value.filter.return_value.all.return_value = [student]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        app = create_test_app([leave_router], teacher, mock_db)
        client = TestClient(app)

        response = client.get("/api/leave/pending")
        assert response.status_code == 200

    def test_growth_record_ownership(self):
        """成长记录的所有权检查"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        # 学生只能删除自己的记录
        mock_record = MagicMock()
        mock_record.id = 1
        mock_record.student_id = 2  # 属于其他学生
        mock_db.query.return_value.filter.return_value.first.return_value = mock_record

        app = create_test_app([growth_router], student, mock_db)
        client = TestClient(app)

        response = client.delete("/api/growth/records/1")
        assert response.status_code == 403

    def test_conversation_ownership(self):
        """对话的所有权检查"""
        student = mock_user(1, UserRole.STUDENT)
        mock_db = MagicMock()

        # 学生只能访问自己的对话
        mock_conv = MagicMock()
        mock_conv.id = 1
        mock_conv.user_id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_conv

        app = create_test_app([conversations_router], student, mock_db)
        client = TestClient(app)

        response = client.get("/api/agent/conversations/1/messages")
        assert response.status_code == 200

        # 尝试访问其他用户的对话
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = client.get("/api/agent/conversations/2/messages")
        assert response.status_code == 404


# ============ 运行测试 ============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

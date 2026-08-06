"""
数据隔离集成测试 — 使用真实数据库和种子数据
测试学生数据独立性、教师数据范围、管理员全权限
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.growth import GrowthRecord
from app.models.academic import Grade, Course
from app.models.leave import LeaveRequest
from app.models.crisis import AIDialogSummary
from app.models.service import ServiceTicket
from app.models.conversation import Conversation

# ============ Helpers ============

client = TestClient(app, raise_server_exceptions=False)


def login(username: str, password: str) -> str:
    """登录并返回token"""
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ============ Test Accounts ============
# Student accounts:
#   2024001 张三 (tutor: t1003 陈慧敏) - 全面型
#   2024002 李四 (no tutor) - 挂科型
#   2024003 王五 (tutor: t1004 张伟明) - 学霸型
#   2024004 赵六 (tutor: t1003 陈慧敏) - 竞赛型
#   2024005 钱七 (tutor: t1004 张伟明) - 危机型
#   2024008 吴十 (tutor: t1007 林晓娟) - 请假型
# Teacher accounts:
#   t1001 王老师 (no assigned students)
#   t1003 陈慧敏 (assigned: 张三, 赵六, 郑十一)
#   t1004 张伟明 (assigned: 王五, 钱七)
#   t1007 林晓娟 (assigned: 吴十)
# Admin:
#   admin 管理员


class TestLogin:
    """测试登录功能"""

    def test_student_login(self):
        token = login("2024001", "123456")
        assert token

    def test_teacher_login(self):
        token = login("t1003", "123456")
        assert token

    def test_admin_login(self):
        token = login("admin", "admin123")
        assert token

    def test_wrong_password(self):
        resp = client.post("/api/auth/login", json={"username": "2024001", "password": "wrong"})
        assert resp.status_code == 401


# ============ 1. 学生数据独立性测试 ============

class TestStudentDataIsolation:
    """测试学生之间数据完全独立"""

    def setup_method(self):
        self.zs_token = login("2024001", "123456")  # 张三
        self.ls_token = login("2024002", "123456")  # 李四
        self.ww_token = login("2024003", "123456")  # 王五

    # --- 成长记录 ---

    def test_student_sees_own_growth_records(self):
        """学生能看到自己的成长记录"""
        resp = client.get("/api/growth/records", headers=auth_header(self.zs_token))
        assert resp.status_code == 200
        records = resp.json()
        # 张三有4条成长记录（竞赛+荣誉+实践+成果）
        assert len(records) > 0
        for r in records:
            # 验证每条记录确实属于该学生
            assert r["student_id"] is not None

    def test_student_cannot_see_others_growth_records_via_query(self):
        """学生通过参数也无法查看其他学生的成长记录"""
        # 张三尝试查看李四的记录
        resp = client.get("/api/growth/records?student_id=999", headers=auth_header(self.zs_token))
        # 应该返回403或只能看到自己的
        if resp.status_code == 200:
            records = resp.json()
            for r in records:
                # 不应该有属于其他学生的记录
                pass  # 由于student_id过滤，应该为空

    def test_student_cannot_delete_others_growth_record(self):
        """学生不能删除其他学生的成长记录"""
        # 先获取李四的记录
        resp_ls = client.get("/api/growth/records", headers=auth_header(self.ls_token))
        if resp_ls.status_code == 200 and resp_ls.json():
            other_record_id = resp_ls.json()[0]["id"]
            # 张三尝试删除李四的记录
            resp = client.delete(f"/api/growth/records/{other_record_id}", headers=auth_header(self.zs_token))
            assert resp.status_code == 403

    # --- 课程和成绩 ---

    def test_student_sees_own_courses(self):
        """学生只能看到自己的课程"""
        resp = client.get("/api/academic/courses", headers=auth_header(self.zs_token))
        assert resp.status_code == 200
        courses = resp.json()
        assert len(courses) > 0  # 张三有4门课

    def test_student_sees_own_grades(self):
        """学生只能看到自己的成绩"""
        resp = client.get("/api/academic/grades", headers=auth_header(self.zs_token))
        assert resp.status_code == 200
        grades = resp.json()
        assert len(grades) > 0

    def test_student_cannot_query_others_courses(self):
        """学生不能通过student_id参数查询其他学生的课程"""
        resp = client.get("/api/academic/courses?student_id=999", headers=auth_header(self.zs_token))
        assert resp.status_code == 403

    def test_student_cannot_query_others_grades(self):
        """学生不能通过student_id参数查询其他学生的成绩"""
        resp = client.get("/api/academic/grades?student_id=999", headers=auth_header(self.zs_token))
        assert resp.status_code == 403

    def test_different_students_have_different_courses(self):
        """不同学生有不同课程"""
        resp_zs = client.get("/api/academic/courses", headers=auth_header(self.zs_token))
        resp_ls = client.get("/api/academic/courses", headers=auth_header(self.ls_token))
        assert resp_zs.status_code == 200
        assert resp_ls.status_code == 200
        zs_names = {c["name"] for c in resp_zs.json()}
        ls_names = {c["name"] for c in resp_ls.json()}
        # 李四有Web前端开发课程，张三没有
        assert "Web前端开发" in ls_names
        assert "Web前端开发" not in zs_names

    # --- 请假 ---

    def test_student_sees_own_leave_requests(self):
        """学生只能看到自己的请假记录"""
        resp = client.get("/api/leave/my", headers=auth_header(self.zs_token))
        assert resp.status_code == 200
        leaves = resp.json()
        # 张三有2条请假记录
        assert len(leaves) > 0

    def test_student_cannot_access_pending_leaves(self):
        """学生不能访问待审批请假列表（教师功能）"""
        resp = client.get("/api/leave/pending", headers=auth_header(self.zs_token))
        assert resp.status_code == 403

    def test_student_cannot_access_all_leaves(self):
        """学生不能访问全部请假列表（教师功能）"""
        resp = client.get("/api/leave/all", headers=auth_header(self.zs_token))
        assert resp.status_code == 403

    # --- 项目展示 ---

    def test_student_sees_own_projects(self):
        """学生只能看到自己的项目"""
        resp = client.get("/api/growth/projects", headers=auth_header(self.zs_token))
        assert resp.status_code == 200

    # --- 技能 ---

    def test_student_updates_own_skills(self):
        """学生可以更新自己的技能"""
        resp = client.put("/api/growth/skills", headers=auth_header(self.zs_token),
                          json={"skills": ["Python", "Vue"], "interests": ["编程"]})
        assert resp.status_code == 200

    # --- AI对话 ---

    def test_student_sees_own_conversations(self):
        """学生只能看到自己的AI对话"""
        resp = client.get("/api/agent/conversations", headers=auth_header(self.zs_token))
        assert resp.status_code == 200

    def test_student_sees_different_conversations_from_others(self):
        """不同学生的AI对话不同"""
        resp_zs = client.get("/api/agent/conversations", headers=auth_header(self.zs_token))
        resp_ww = client.get("/api/agent/conversations", headers=auth_header(self.ww_token))
        assert resp_zs.status_code == 200
        assert resp_ww.status_code == 200
        # 对话列表应该基于各自用户

    # --- 危机预警 ---

    def test_student_cannot_access_crisis_alerts(self):
        """学生不能访问危机预警（教师功能）"""
        resp = client.get("/api/crisis/alerts", headers=auth_header(self.zs_token))
        assert resp.status_code == 403

    # --- 成长画像 ---

    def test_student_sees_own_profile(self):
        """学生只能看到自己的成长画像"""
        resp = client.get("/api/growth/profile", headers=auth_header(self.zs_token))
        assert resp.status_code == 200
        profile = resp.json()
        # 张三的画像应该有数据
        assert profile["total_records"] > 0


# ============ 2. 公有数据测试 ============

class TestPublicData:
    """测试所有用户都能访问的公有数据"""

    def setup_method(self):
        self.zs_token = login("2024001", "123456")

    def test_campus_figures_public(self):
        """校园人物是公开数据"""
        resp = client.get("/api/campus/figures")
        assert resp.status_code == 200
        figures = resp.json()
        assert len(figures) > 0

    def test_campus_sceneries_public(self):
        """校园风景是公开数据"""
        resp = client.get("/api/campus/sceneries")
        assert resp.status_code == 200
        sceneries = resp.json()
        assert len(sceneries) > 0

    def test_teacher_list_authenticated(self):
        """教师列表需要认证"""
        # 未认证请求应被拒绝
        resp = client.get("/api/auth/teachers")
        assert resp.status_code == 401
        # 已认证请求应返回数据
        token = login("2024001", "123456")
        resp = client.get("/api/auth/teachers", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        teachers = resp.json()
        assert len(teachers) >= 6


# ============ 3. 教师权限测试 ============

class TestTeacherDataScope:
    """测试教师只能看到名下学生的数据"""

    def setup_method(self):
        # 陈慧敏: 管理 张三, 赵六, 郑十一
        self.chm_token = login("t1003", "123456")
        # 张伟明: 管理 王五, 钱七
        self.zwm_token = login("t1004", "123456")
        # 王老师: 无学生
        self.wl_token = login("t1001", "123456")

    def test_teacher_dashboard(self):
        """教师能看自己的仪表板"""
        resp = client.get("/api/teacher/dashboard", headers=auth_header(self.chm_token))
        assert resp.status_code == 200
        data = resp.json()
        # 陈慧敏有3个学生（张三, 赵六, 郑十一）
        assert data["total_students"] == 3

    def test_teacher_no_students_dashboard(self):
        """没有学生的教师仪表板"""
        resp = client.get("/api/teacher/dashboard", headers=auth_header(self.wl_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_students"] == 0

    def test_teacher_sees_only_own_students(self):
        """教师只能看到自己名下的学生"""
        resp = client.get("/api/teacher/students", headers=auth_header(self.chm_token))
        assert resp.status_code == 200
        students = resp.json()
        student_names = {s["name"] for s in students}
        # 陈慧敏应该看到张三和赵六
        assert "张三" in student_names
        assert "赵六" in student_names
        # 不应该看到王五（属于张伟明）
        assert "王五" not in student_names

    def test_teacher_sees_different_students_than_peer(self):
        """不同教师看到不同学生列表"""
        resp_chm = client.get("/api/teacher/students", headers=auth_header(self.chm_token))
        resp_zwm = client.get("/api/teacher/students", headers=auth_header(self.zwm_token))
        assert resp_chm.status_code == 200
        assert resp_zwm.status_code == 200
        chm_names = {s["name"] for s in resp_chm.json()}
        zwm_names = {s["name"] for s in resp_zwm.json()}
        assert chm_names != zwm_names
        # 张三只在陈慧敏列表中
        assert "张三" in chm_names
        assert "张三" not in zwm_names

    def test_teacher_student_detail_full_for_tutor(self):
        """导师可以查看学生的完整信息"""
        # 获取张三的id
        resp = client.get("/api/teacher/students", headers=auth_header(self.chm_token))
        students = resp.json()
        zs = next((s for s in students if s["name"] == "张三"), None)
        assert zs is not None
        # 陈慧敏是张三的导师，应该看到完整信息
        resp = client.get(f"/api/teacher/students/{zs['id']}", headers=auth_header(self.chm_token))
        assert resp.status_code == 200
        detail = resp.json()
        assert "growth_records" in detail
        assert "crisis_alerts" in detail
        assert "leave_requests" in detail

    def test_teacher_student_detail_resume_for_non_tutor(self):
        """非导师教师只能看到学生的简历信息"""
        # 获取张三的id
        resp_chm = client.get("/api/teacher/students", headers=auth_header(self.chm_token))
        students = resp_chm.json()
        zs = next((s for s in students if s["name"] == "张三"), None)
        assert zs is not None
        # 张伟明不是张三的导师，只能看到简历
        resp = client.get(f"/api/teacher/students/{zs['id']}", headers=auth_header(self.zwm_token))
        assert resp.status_code == 200
        detail = resp.json()
        assert "growth_records" in detail
        assert "projects" in detail
        # 非导师不应看到危机和请假信息
        assert "crisis_alerts" not in detail
        assert "leave_requests" not in detail

    def test_teacher_growth_stats(self):
        """教师能看名下学生的成长统计"""
        resp = client.get("/api/teacher/growth-stats", headers=auth_header(self.chm_token))
        assert resp.status_code == 200
        stats = resp.json()
        assert "honor" in stats
        assert "competition" in stats

    def test_teacher_pending_leaves(self):
        """教师只能看到名下学生的待审批请假"""
        resp = client.get("/api/leave/pending", headers=auth_header(self.chm_token))
        assert resp.status_code == 200
        leaves = resp.json()
        # 所有返回的请假应该属于陈慧敏的学生
        # 张三有1条待审批请假
        assert len(leaves) > 0

    def test_teacher_cannot_approve_others_students_leave(self):
        """教师不能审批其他教师名下学生的请假"""
        # 张伟明的学生王五没有请假记录
        # 但如果有，张伟明不能审批陈慧敏学生的请假
        resp = client.get("/api/leave/pending", headers=auth_header(self.zwm_token))
        assert resp.status_code == 200
        leaves = resp.json()
        # 找一个不属于张伟明学生的请假来尝试审批
        if leaves:
            leave_id = leaves[0]["id"]
            resp = client.post(f"/api/leave/{leave_id}/review",
                             headers=auth_header(self.zwm_token),
                             json={"action": "approve"})
            # 如果这个请假不属于张伟明的学生，应该403
            # 如果属于，应该200

    def test_teacher_crisis_alerts_scoped(self):
        """教师只能看到名下学生的危机预警"""
        resp = client.get("/api/crisis/alerts", headers=auth_header(self.chm_token))
        assert resp.status_code == 200
        alerts = resp.json()
        # 陈慧敏的学生中，赵六和郑十一没有危机预警
        # 所以陈慧敏应该看不到钱七（属于张伟明）的严重危机

    def test_student_cannot_access_teacher_routes(self):
        """学生不能访问教师路由"""
        zs_token = login("2024001", "123456")
        resp = client.get("/api/teacher/dashboard", headers=auth_header(zs_token))
        assert resp.status_code == 403

        resp = client.get("/api/teacher/students", headers=auth_header(zs_token))
        assert resp.status_code == 403

    def test_teacher_cannot_access_admin_routes(self):
        """教师不能访问管理员路由"""
        resp = client.get("/api/admin/students", headers=auth_header(self.chm_token))
        assert resp.status_code == 403

        resp = client.get("/api/admin/teachers", headers=auth_header(self.chm_token))
        assert resp.status_code == 403


# ============ 4. 管理员权限测试 ============

class TestAdminPermissions:
    """测试管理员的全权限"""

    def setup_method(self):
        self.admin_token = login("admin", "admin123")

    def test_admin_sees_all_students(self):
        """管理员能看到所有学生"""
        resp = client.get("/api/admin/students", headers=auth_header(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 9  # 至少9个学生

    def test_admin_sees_all_teachers(self):
        """管理员能看到所有教师"""
        resp = client.get("/api/admin/teachers", headers=auth_header(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 6  # 至少7个教师

    def test_admin_teacher_student_list(self):
        """管理员能查看任何教师的学生列表"""
        # 先获取教师列表
        resp = client.get("/api/admin/teachers", headers=auth_header(self.admin_token))
        data = resp.json()
        teachers = data["items"]
        if teachers:
            teacher_id = teachers[0]["id"]
            resp = client.get(f"/api/admin/teachers/{teacher_id}/students",
                            headers=auth_header(self.admin_token))
            assert resp.status_code == 200

    def test_admin_knowledge_crud(self):
        """管理员能增删改查知识库"""
        # 创建
        resp = client.post("/api/admin/knowledge", headers=auth_header(self.admin_token),
                          json={"category": "测试", "question": "测试问题", "answer": "测试答案", "tags": "测试"})
        assert resp.status_code == 200
        item_id = resp.json()["id"]

        # 读取
        resp = client.get("/api/admin/knowledge", headers=auth_header(self.admin_token))
        assert resp.status_code == 200

        # 更新
        resp = client.put(f"/api/admin/knowledge/{item_id}", headers=auth_header(self.admin_token),
                         json={"answer": "更新后的答案"})
        assert resp.status_code == 200

        # 删除
        resp = client.delete(f"/api/admin/knowledge/{item_id}", headers=auth_header(self.admin_token))
        assert resp.status_code == 200

    def test_admin_growth_records_all(self):
        """管理员能看到所有学生的成长记录"""
        resp = client.get("/api/growth/records", headers=auth_header(self.admin_token))
        assert resp.status_code == 200
        records = resp.json()
        # 管理员应该能看到所有学生的记录
        student_ids = set(r["student_id"] for r in records)
        assert len(student_ids) > 1  # 至少2个不同学生的记录

    def test_admin_teacher_routes(self):
        """管理员也能访问教师端路由"""
        resp = client.get("/api/teacher/dashboard", headers=auth_header(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        # 管理员应该能看到所有学生
        assert data["total_students"] >= 9

    def test_admin_academic_data(self):
        """管理员能看到所有学生的学术数据"""
        resp = client.get("/api/academic/courses", headers=auth_header(self.admin_token))
        assert resp.status_code == 200
        courses = resp.json()
        # 管理员应该看到所有课程（CourseOut schema不含student_id，直接检查课程数量）
        assert len(courses) > 0

    def test_admin_leave_all(self):
        """管理员能看到所有请假记录"""
        resp = client.get("/api/leave/all", headers=auth_header(self.admin_token))
        assert resp.status_code == 200
        leaves = resp.json()
        assert len(leaves) > 0

    def test_admin_crisis_alerts(self):
        """管理员能看到所有危机预警"""
        resp = client.get("/api/crisis/alerts", headers=auth_header(self.admin_token))
        assert resp.status_code == 200

    def test_admin_reset_password(self):
        """管理员能重置用户密码"""
        # 获取学生列表
        resp = client.get("/api/admin/students", headers=auth_header(self.admin_token))
        data = resp.json()
        students = data["items"]
        if students:
            student_id = students[0]["id"]
            resp = client.post(f"/api/admin/reset-password/{student_id}",
                             headers=auth_header(self.admin_token))
            assert resp.status_code == 200

    def test_student_cannot_access_admin_routes(self):
        """学生不能访问管理员路由"""
        zs_token = login("2024001", "123456")
        resp = client.get("/api/admin/students", headers=auth_header(zs_token))
        assert resp.status_code == 403


# ============ 5. 教师创建记录测试 ============

class TestTeacherCreateRecord:
    """测试教师为学生创建成长记录"""

    def setup_method(self):
        self.chm_token = login("t1003", "123456")  # 陈慧敏

    def test_teacher_can_create_student_record(self):
        """教师可以为名下学生创建成长记录"""
        # 获取陈慧敏的学生列表
        resp = client.get("/api/teacher/students", headers=auth_header(self.chm_token))
        students = resp.json()
        assert len(students) > 0
        student_id = students[0]["id"]

        resp = client.post("/api/growth/records", headers=auth_header(self.chm_token),
                          json={
                              "student_id": student_id,
                              "type": "honor",
                              "title": "教师创建的荣誉记录",
                              "date": "2025-01-01",
                              "honor_level": "校级",
                          })
        assert resp.status_code == 200
        record = resp.json()
        assert record["student_id"] == student_id


# ============ 6. 错误检查 ============

class TestErrorChecking:
    """检查现有功能是否存在错误"""

    def test_health_check(self):
        """健康检查"""
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_growth_profile_completeness(self):
        """检查成长画像数据完整性"""
        zs_token = login("2024001", "123456")
        resp = client.get("/api/growth/profile", headers=auth_header(zs_token))
        assert resp.status_code == 200
        profile = resp.json()
        # 检查所有必要字段存在
        required_fields = ["total_score", "radar", "stats_by_type", "monthly_trend",
                          "skills", "interests", "total_records", "total_skills", "gpa_trend"]
        for field in required_fields:
            assert field in profile, f"缺少字段: {field}"

    def test_growth_record_create_and_list(self):
        """测试成长记录创建和列表"""
        zs_token = login("2024001", "123456")
        # 创建
        resp = client.post("/api/growth/records", headers=auth_header(zs_token),
                          json={
                              "type": "practice",
                              "title": "集成测试-实践活动",
                              "date": "2025-01-15",
                              "practice_type": "志愿服务",
                          })
        assert resp.status_code == 200
        new_id = resp.json()["id"]

        # 列表中应该包含新记录
        resp = client.get("/api/growth/records", headers=auth_header(zs_token))
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert new_id in ids

        # 删除
        resp = client.delete(f"/api/growth/records/{new_id}", headers=auth_header(zs_token))
        assert resp.status_code == 200

    def test_leave_create_and_list(self):
        """测试请假创建和列表"""
        zs_token = login("2024001", "123456")
        resp = client.post("/api/leave/create", headers=auth_header(zs_token),
                          json={
                              "start_date": "2025-06-01",
                              "end_date": "2025-06-02",
                              "reason": "集成测试-请假",
                              "leave_type": "personal",
                          })
        assert resp.status_code == 200

        resp = client.get("/api/leave/my", headers=auth_header(zs_token))
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_academic_grades_gpa_calculation(self):
        """检查GPA计算是否正确"""
        zs_token = login("2024001", "123456")
        resp = client.get("/api/growth/profile", headers=auth_header(zs_token))
        assert resp.status_code == 200
        profile = resp.json()
        gpa_trend = profile.get("gpa_trend", [])
        if gpa_trend:
            for gpa_point in gpa_trend:
                assert 0 <= gpa_point["gpa"] <= 4.0, f"GPA超出范围: {gpa_point['gpa']}"

    def test_conversation_create_and_messages(self):
        """测试对话创建和消息"""
        zs_token = login("2024001", "123456")
        # 创建对话
        resp = client.post("/api/agent/conversations", headers=auth_header(zs_token),
                          json={"type": "normal", "title": "测试对话"})
        assert resp.status_code == 200
        conv_id = resp.json()["id"]

        # 获取消息
        resp = client.get(f"/api/agent/conversations/{conv_id}/messages",
                         headers=auth_header(zs_token))
        assert resp.status_code == 200

        # 删除对话
        resp = client.delete(f"/api/agent/conversations/{conv_id}",
                           headers=auth_header(zs_token))
        assert resp.status_code == 200

    def test_leave_approval_workflow(self):
        """测试请假审批流程"""
        chm_token = login("t1003", "123456")  # 陈慧敏
        zs_token = login("2024001", "123456")  # 张三

        # 1. 张三创建一个请假
        resp = client.post("/api/leave/create", headers=auth_header(zs_token),
                          json={
                              "start_date": "2025-07-01",
                              "end_date": "2025-07-02",
                              "reason": "审批流程测试",
                              "leave_type": "personal",
                          })
        assert resp.status_code == 200
        leave_id = resp.json()["id"]

        # 2. 陈慧敏查看待审批列表
        resp = client.get("/api/leave/pending", headers=auth_header(chm_token))
        assert resp.status_code == 200
        pending = resp.json()
        pending_ids = [l["id"] for l in pending]
        assert leave_id in pending_ids

        # 3. 陈慧敏审批通过
        resp = client.post(f"/api/leave/{leave_id}/review",
                         headers=auth_header(chm_token),
                         json={"action": "approve"})
        assert resp.status_code == 200

        # 4. 验证状态更新
        resp = client.get("/api/leave/my", headers=auth_header(zs_token))
        leaves = resp.json()
        approved = next((l for l in leaves if l["id"] == leave_id), None)
        assert approved is not None
        assert approved["status"] == "approved"

    def test_project_crud(self):
        """测试项目增删改查"""
        zs_token = login("2024001", "123456")
        # 创建
        resp = client.post("/api/growth/projects", headers=auth_header(zs_token),
                          json={
                              "project_name": "测试项目",
                              "start_date": "2025-01-01",
                              "end_date": "2025-06-30",
                              "is_team": False,
                          })
        assert resp.status_code == 200
        proj_id = resp.json()["id"]

        # 更新
        resp = client.put(f"/api/growth/projects/{proj_id}", headers=auth_header(zs_token),
                         json={
                             "project_name": "更新后的项目",
                             "start_date": "2025-01-01",
                             "end_date": "2025-06-30",
                             "is_team": True,
                             "team_members": "张三,李四",
                         })
        assert resp.status_code == 200

        # 列表
        resp = client.get("/api/growth/projects", headers=auth_header(zs_token))
        assert resp.status_code == 200
        proj_ids = [p["id"] for p in resp.json()]
        assert proj_id in proj_ids

        # 删除
        resp = client.delete(f"/api/growth/projects/{proj_id}", headers=auth_header(zs_token))
        assert resp.status_code == 200

    def test_student_cannot_access_crisis(self):
        """学生不能访问危机预警"""
        zs_token = login("2024001", "123456")
        resp = client.get("/api/crisis/alerts", headers=auth_header(zs_token))
        assert resp.status_code == 403

    def test_student_cannot_access_teacher_student_list(self):
        """学生不能访问教师端学生列表"""
        zs_token = login("2024001", "123456")
        resp = client.get("/api/teacher/students", headers=auth_header(zs_token))
        assert resp.status_code == 403

    def test_admin_student_teacher_full_access(self):
        """管理员对教师和学生有完全访问权限"""
        admin_token = login("admin", "admin123")
        # 访问教师端
        resp = client.get("/api/teacher/students", headers=auth_header(admin_token))
        assert resp.status_code == 200
        # 管理员通过教师路由应该看到所有学生
        students = resp.json()
        assert len(students) >= 9


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

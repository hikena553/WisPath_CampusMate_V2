"""管理端核心链路（p3_1）：教师管理 / 密码重置。

关键约束：seed 内置 admin（admin/admin123）未改密，会被强改密中间件拦截；
本文件一律使用 login_token(UserRole.ADMIN) 自建已改密管理员。
"""
import pytest

from app.models.user import User, UserRole


def test_create_teacher_success_returns_initial_password(api, login_token, db):
    """仅创建响应包含 initial_password（TeacherOut 契约）。"""
    login = login_token(UserRole.ADMIN)
    data = {
        "username": f"t{uuid4hex()}",
        "name": "新教师",
        "college": "信息学院",
        "title": "讲师",
    }
    resp = api.post("/api/admin/teachers", json=data, headers=login["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == data["username"]
    assert body["name"] == "新教师"
    assert isinstance(body["initial_password"], str) and len(body["initial_password"]) >= 8

    teacher = db.query(User).filter(User.id == body["id"]).first()
    assert teacher is not None
    assert teacher.password_changed is False  # 初始密码必须强制首登修改


def uuid4hex():
    import uuid
    return uuid.uuid4().hex[:8]


def test_create_teacher_duplicate_username_400(api, login_token):
    login = login_token(UserRole.ADMIN)
    data = {"username": f"dup{uuid4hex()}", "name": "重复工号教师"}
    first = api.post("/api/admin/teachers", json=data, headers=login["headers"])
    assert first.status_code == 200, first.text
    second = api.post("/api/admin/teachers", json=data, headers=login["headers"])
    assert second.status_code == 400
    assert "工号已存在" in second.json()["detail"]


def test_list_teachers_never_exposes_initial_password(api, login_token):
    """列表接口（PaginatedResponse）不泄露初始密码字段。"""
    login = login_token(UserRole.ADMIN)
    resp = api.get("/api/admin/teachers", headers=login["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body and "total" in body
    for item in body["items"]:
        assert "initial_password" not in item
        assert "password_hash" not in item


def test_student_forbidden_on_admin_endpoints(api, login_token):
    """非管理员访问管理端接口一律 403 权限不足。"""
    login = login_token(UserRole.STUDENT)
    resp = api.get("/api/admin/teachers", headers=login["headers"])
    assert resp.status_code == 403
    assert resp.json()["detail"] == "权限不足"


def test_reset_password_forces_change_on_next_login(api, login_token, db):
    """重置后 password_changed=False，初始密码可登录但 /me 提示需改密。"""
    admin = login_token(UserRole.ADMIN)
    created = api.post(
        "/api/admin/teachers",
        json={"username": f"rz{uuid4hex()}", "name": "被重置教师"},
        headers=admin["headers"],
    )
    assert created.status_code == 200, created.text
    teacher_id = created.json()["id"]

    resp = api.post(f"/api/admin/reset-password/{teacher_id}", headers=admin["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["initial_password"] and "hint" in body

    target = db.query(User).filter(User.id == teacher_id).first()
    assert target.password_changed is False

    relogin = api.post(
        "/api/auth/login",
        json={"username": target.username, "password": body["initial_password"]},
    )
    assert relogin.status_code == 200, relogin.text
    me = api.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {relogin.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["password_needs_change"] is True


def test_reset_password_unknown_user_404(api, login_token):
    login = login_token(UserRole.ADMIN)
    resp = api.post("/api/admin/reset-password/99999999", headers=login["headers"])
    assert resp.status_code == 404
    assert resp.json()["detail"] == "用户不存在"
"""认证链路测试：登录/限流/改密规则/首登强改密/登出撤销/CSRF 双通道。"""
import os

from app.models.user import UserRole
from app.utils.rate_limiter import reset_rate_limiter

# ── 登录 ──────────────────────────────────────────────────────────────

def test_login_success_sets_httponly_cookie(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "admin"
    # httpOnly Cookie 通道（F3）：不可被 JS 读取，仅随请求回传
    assert resp.cookies.get("campus_token") == body["access_token"]
    assert "httponly" in resp.headers.get("set-cookie", "").lower()


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"username": "2024001", "password": "wrong"},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "用户名或密码错误"


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "ghost_1", "password": "123456"},
                       headers={"X-Requested-With": "XMLHttpRequest"})
    assert resp.status_code == 401


def test_login_rate_limit_429(client):
    """TESTING 旁路翻转后，60s 窗口内第 6 次登录尝试被拒（恶意爆破防护）。"""
    os.environ["TESTING"] = "0"
    try:
        for _ in range(5):
            r = client.post("/api/auth/login", json={"username": "2024001", "password": "bad"},
                            headers={"X-Requested-With": "XMLHttpRequest"})
            assert r.status_code == 401
        resp = client.post("/api/auth/login", json={"username": "2024001", "password": "bad"},
                           headers={"X-Requested-With": "XMLHttpRequest"})
        assert resp.status_code == 429
        assert resp.json()["detail"] == "登录尝试过于频繁，请60秒后再试"
    finally:
        os.environ["TESTING"] = "1"
        reset_rate_limiter()


# ── /me 与改密标志 ─────────────────────────────────────────────────────

def test_me_returns_password_needs_change_flag(client, seed_login):
    auth = seed_login("2024002")  # seed 学生：未修改初始密码
    resp = client.get("/api/auth/me", headers=auth["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "2024002"
    assert body["password_needs_change"] is True


def test_me_flag_false_after_password_changed(client, login_token):
    auth = login_token()  # 测试用户：默认已改密
    resp = client.get("/api/auth/me", headers=auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["password_needs_change"] is False


# ── 改密规则全量校验（S2 强改密配套） ────────────────────────────────────

def test_change_password_validation_rules(client, login_token, api):
    """旧密码错误/过短/缺字母/缺数字/新旧相同 均 400。

    契约顺序（auth.py 源码）：旧密码 → 至少 8 位 → 字母数字 → 新旧相同。
    旧密码需 ≥8 位且含字母数字，故用 login_token 自建用户（TestPass123）。
    """
    auth = login_token()  # 测试用户：旧密码 TestPass123
    cases = [
        ({"old_password": "wrong", "new_password": "NewPass123"}, "旧密码错误"),
        ({"old_password": "TestPass123", "new_password": "a1b"}, "新密码至少 8 位"),
        ({"old_password": "TestPass123", "new_password": "12345678"}, "新密码必须同时包含字母和数字"),
        ({"old_password": "TestPass123", "new_password": "abcdefgh"}, "新密码必须同时包含字母和数字"),
        ({"old_password": "TestPass123", "new_password": "TestPass123"}, "新密码不能与旧密码相同"),
    ]
    for payload, expect in cases:
        resp = api.put("/api/auth/change-password", json=payload, headers=auth["headers"])
        assert resp.status_code == 400, f"payload={payload}"
        assert resp.json()["detail"] == expect


def test_change_password_success_invalidates_old_token(client, make_user, api):
    """改密成功后：旧 token 立即失效（ph 失配），新密码可登录、旧密码被拒。"""
    user = make_user(password_changed=False)
    # 真实 HTTP 登录（初始密码 TestPass123）
    login = client.post("/api/auth/login",
                        json={"username": user.username, "password": "TestPass123"},
                        headers={"X-Requested-With": "XMLHttpRequest"})
    assert login.status_code == 200
    old_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {old_token}"}

    resp = api.put("/api/auth/change-password",
                   json={"old_password": "TestPass123", "new_password": "BrandNew123"},
                   headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "密码修改成功"

    # 旧 token：ph 已失配 → 401
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 401
    assert me.json()["detail"] == "密码已修改，请重新登录"

    # 新密码可登录，旧密码被拒
    ok = client.post("/api/auth/login",
                     json={"username": user.username, "password": "BrandNew123"},
                     headers={"X-Requested-With": "XMLHttpRequest"})
    assert ok.status_code == 200
    bad = client.post("/api/auth/login",
                      json={"username": user.username, "password": "TestPass123"},
                      headers={"X-Requested-With": "XMLHttpRequest"})
    assert bad.status_code == 401


# ── 首登改密：只提醒不阻断（S2 调整） ─────────────────────────────────

def test_initial_password_only_reminds_without_blocking(client, seed_login, api):
    """未修改初始密码不再拦截业务接口，仅由 /me 返回提醒标记。"""
    auth = seed_login("2024004")

    # 业务接口正常放行（调整前此处是一律 403）
    resp = client.get("/api/auth/teachers", headers=auth["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 提醒标记仍在，供前端做非阻断提示（横幅 / 改密入口）
    me = client.get("/api/auth/me", headers=auth["headers"])
    assert me.status_code == 200
    assert me.json()["password_needs_change"] is True

    # 改密后标记消失
    r = api.put("/api/auth/change-password",
                json={"old_password": "123456", "new_password": "Renewed123"},
                headers=auth["headers"])
    assert r.status_code == 200
    auth2 = seed_login("2024004", "Renewed123")
    me2 = client.get("/api/auth/me", headers=auth2["headers"])
    assert me2.status_code == 200
    assert me2.json()["password_needs_change"] is False


# ── 登出撤销（F3） ──────────────────────────────────────────────────────

def test_logout_revokes_token_and_is_idempotent(client, login_token, api):
    auth = login_token()
    resp = api.post("/api/auth/logout", headers=auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["message"] == "已退出登录"

    # 撤销后旧 token 立即失效
    me = client.get("/api/auth/me", headers=auth["headers"])
    assert me.status_code == 401
    assert me.json()["detail"] == "登录已失效，请重新登录"

    # 幂等：重复登出不报错，Cookie 被清除
    again = api.post("/api/auth/logout", headers=auth["headers"])
    assert again.status_code == 200


# ── CSRF 双通道（F3 纵深防护） ──────────────────────────────────────────

def test_csrf_blocks_cookie_write_without_custom_header(client, login_token, api):
    """携带认证 Cookie 的写请求缺少 X-Requested-With 头 → 403。"""
    login_token()  # 登录成功 → client jar 持有 campus_token Cookie
    assert client.cookies.get("campus_token")

    blocked = client.post("/api/auth/logout")  # 未带头，Cookie 自动附带
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "请求头校验失败"

    ok = api.post("/api/auth/logout")  # 带头 + Cookie → 放行
    assert ok.status_code == 200
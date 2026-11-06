"""QQ 互联移动端（Android SDK 直通）登录 / 绑定 / 注册链路。

凭证核验统一 mock graph.qq.com 响应，不触外网。覆盖：
- verify_mobile_token 的伪造 / 不一致拒绝
- mobile/authorize：未绑定下发注册票据、已绑定直接登录、MEDIA/ADMIN 拒绝
- mobile/bind：成功、占用冲突、未登录
- QQ 票据注册：手机号选填（存量链路在此处会 400）
"""
import json
import secrets
import uuid

import pytest

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.academic import College, Major
from app.models.user import User, UserRole
from app.services import qq_oauth_service

MOCK_APP_ID = "1906302158"
MOCK_NICKNAME = "校园小明"


class _FakeResp:
    def __init__(self, payload):
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    def json(self):
        return json.loads(self.text)


class _FakeHttpx:
    """只响应 qq_oauth_service 会访问的两个 graph.qq.com 端点。"""

    def __init__(self, me_payload):
        self.me_payload = me_payload
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if url == qq_oauth_service.QQ_ME_URL:
            return _FakeResp(self.me_payload)
        if url == qq_oauth_service.QQ_USER_INFO_URL:
            return _FakeResp({"ret": 0, "nickname": MOCK_NICKNAME})
        raise AssertionError(f"意外请求: {url}")


def _mock_qq(monkeypatch, openid: str, client_id: str = MOCK_APP_ID) -> _FakeHttpx:
    """/me 固定返回给定 openid（client_id 可伪造），模拟腾讯核验结果。"""
    fake = _FakeHttpx({"client_id": client_id, "openid": openid})
    monkeypatch.setattr(qq_oauth_service, "httpx", fake)
    return fake


@pytest.fixture()
def qq_app_configured(monkeypatch):
    monkeypatch.setattr(settings, "QQ_APP_ID", MOCK_APP_ID, raising=False)
    monkeypatch.setattr(settings, "QQ_APP_KEY", "test-app-key", raising=False)


def _authorize(api, openid: str):
    return api.post(
        "/api/auth/qq/mobile/authorize",
        json={"access_token": "sdk-access-token", "openid": openid},
    )


# ==================== verify_mobile_token ====================


def test_verify_mobile_token_ok(qq_app_configured, monkeypatch):
    _mock_qq(monkeypatch, "openid-abc")
    assert qq_oauth_service.verify_mobile_token("tok", "openid-abc") == MOCK_NICKNAME


def test_verify_mobile_token_rejects_foreign_app(qq_app_configured, monkeypatch):
    _mock_qq(monkeypatch, "openid-abc", client_id="other-app")
    with pytest.raises(RuntimeError):
        qq_oauth_service.verify_mobile_token("tok", "openid-abc")


def test_verify_mobile_token_rejects_openid_mismatch(qq_app_configured, monkeypatch):
    _mock_qq(monkeypatch, "openid-real")
    with pytest.raises(RuntimeError):
        qq_oauth_service.verify_mobile_token("tok", "openid-fake")


def test_verify_mobile_token_rejects_missing_input(qq_app_configured):
    with pytest.raises(RuntimeError):
        qq_oauth_service.verify_mobile_token("", "openid-abc")


# ==================== /qq/mobile/authorize ====================


def test_mobile_authorize_requires_app_id(api, monkeypatch):
    monkeypatch.setattr(settings, "QQ_APP_ID", "", raising=False)
    resp = _authorize(api, "openid-x")
    assert resp.status_code == 503


def test_mobile_authorize_unbound_returns_register_ticket(api, qq_app_configured, monkeypatch):
    _mock_qq(monkeypatch, "openid-new")
    resp = _authorize(api, "openid-new")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "unregistered"
    assert data["nickname"] == MOCK_NICKNAME
    payload = qq_oauth_service.decode_register_ticket(data["register_ticket"])
    assert payload and payload["openid"] == "openid-new"
    assert payload["nickname"] == MOCK_NICKNAME


def test_mobile_authorize_bound_logs_in(api, qq_app_configured, monkeypatch, make_user, db):
    user = make_user(role=UserRole.STUDENT)
    user.qq_openid = "openid-bound"
    db.commit()

    _mock_qq(monkeypatch, "openid-bound")
    resp = _authorize(api, "openid-bound")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "login"
    assert data["login"]["access_token"]
    assert data["login"]["user"]["username"] == user.username
    assert "qq" in data["login"]["quick_channels"]


def test_mobile_authorize_rejects_admin(api, qq_app_configured, monkeypatch, make_user, db):
    user = make_user(role=UserRole.ADMIN)
    user.qq_openid = "openid-admin"
    db.commit()

    _mock_qq(monkeypatch, "openid-admin")
    resp = _authorize(api, "openid-admin")
    assert resp.status_code == 403


def test_mobile_authorize_rejects_bad_token(api, qq_app_configured, monkeypatch):
    # /me 返回错误载荷（无 openid）→ 核验失败
    monkeypatch.setattr(
        qq_oauth_service, "httpx", _FakeHttpx({"error": 100016, "error_description": "invalid token"})
    )
    resp = _authorize(api, "openid-any")
    assert resp.status_code == 401


# ==================== /qq/mobile/bind ====================


def test_mobile_bind_success(api, qq_app_configured, monkeypatch, login_token, db):
    me = login_token(role=UserRole.STUDENT)
    _mock_qq(monkeypatch, "openid-mine")
    resp = api.post(
        "/api/auth/qq/mobile/bind",
        json={"access_token": "tok", "openid": "openid-mine"},
        headers=me["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["qq_bound"] is True
    db.refresh(me["user"])
    assert me["user"].qq_openid == "openid-mine"
    assert me["user"].qq_nickname == MOCK_NICKNAME


def test_mobile_bind_conflict(api, qq_app_configured, monkeypatch, login_token, make_user, db):
    other = make_user(role=UserRole.STUDENT)
    other.qq_openid = "openid-taken"
    db.commit()

    me = login_token(role=UserRole.STUDENT)
    _mock_qq(monkeypatch, "openid-taken")
    resp = api.post(
        "/api/auth/qq/mobile/bind",
        json={"access_token": "tok", "openid": "openid-taken"},
        headers=me["headers"],
    )
    assert resp.status_code == 409


def test_mobile_bind_requires_login(api):
    # 未登录 401 来自依赖（先于业务校验），无需 mock 腾讯侧
    resp = api.post(
        "/api/auth/qq/mobile/bind", json={"access_token": "tok", "openid": "openid-x"}
    )
    assert resp.status_code == 401


# ==================== QQ 票据注册（手机号选填） ====================


def _ensure_college_major(db) -> tuple[int, int]:
    college = db.query(College).first()
    if not college:
        suffix = uuid.uuid4().hex[:6]
        college = College(name=f"测试学院{suffix}", code=f"TQQ{suffix}")
        db.add(college)
        db.flush()
    major = db.query(Major).filter(Major.college_id == college.id).first()
    if not major:
        suffix = uuid.uuid4().hex[:6]
        major = Major(college_id=college.id, name=f"测试专业{suffix}", code=f"TM{suffix}")
        db.add(major)
        db.commit()
        db.refresh(major)
    return college.id, major.id


def test_register_with_qq_ticket_without_phone(api, qq_app_configured, db):
    college_id, major_id = _ensure_college_major(db)
    openid = f"openid-reg-{uuid.uuid4().hex[:8]}"
    ticket = qq_oauth_service.create_register_ticket(openid, MOCK_NICKNAME)
    student_no = "9" + "".join(secrets.choice("0123456789") for _ in range(9))

    resp = api.post(
        "/api/auth/register",
        json={
            "role": "student",
            "student_no": student_no,
            "password": "Abcd1234",
            "name": "戚授权",
            "college_id": college_id,
            "major_id": major_id,
            "phone": None,
            "qq": "123456789",
            "phone_ticket": None,
            "qq_ticket": ticket,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["qq_bound"] is True

    user = db.query(User).filter(User.username == student_no).first()
    assert user is not None
    assert user.qq_openid == openid
    assert user.phone is None

    # 注册即登录返回的 token 可用，账号也能密码登录
    resp2 = api.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert resp2.status_code == 200
    resp3 = api.post("/api/auth/login", json={"username": student_no, "password": "Abcd1234"})
    assert resp3.status_code == 200

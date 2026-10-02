"""pytest 共享基建（p3_1 测试补课）。

关键时序（顺序不可颠倒）：
1. 将 backend 加入 sys.path；
2. 注入 fake magic 模块（CI 无 libmagic，upload 校验用可配置 fake）；
3. 设置环境变量（app.core.config / app.core.database 为模块级单例，
   必须在 import 任何 app.* 模块之前完成，否则 import 即抛异常）；
4. 之后才允许 import app 模块。
"""
import os
import sys
import types
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 测试库绝对路径：SQLite URL 用绝对路径，保证从任意 cwd 运行结果一致（CI 友好）
TEST_DB = BACKEND_DIR / "tests" / "test.db"
TEST_DB.parent.mkdir(parents=True, exist_ok=True)

# ── 1. fake magic（app/api/upload.py 在函数体内 import magic） ────────────
_MAGIC_STATE = {"mime": "image/png"}


def _fake_from_buffer(content: bytes, mime: bool = False) -> str:
    return _MAGIC_STATE["mime"]


_fake_magic = types.ModuleType("magic")
_fake_magic.from_buffer = _fake_from_buffer
sys.modules["magic"] = _fake_magic

# ── 2. 环境变量（先于 app.* 导入） ────────────────────────────────────────
os.environ["TESTING"] = "1"
os.environ["ENV"] = "development"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789abcdef"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ.setdefault("LLM_API_KEY", "test-llm-key")

# ── 3. 之后才导入 app 模块 ────────────────────────────────────────────────
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.feedback import Feedback  # noqa: E402
from app.models.conversation import Conversation, ConversationMessage  # noqa: E402
from app.models.crisis import AIDialogSummary  # noqa: E402
from app.models.profile import StudentProfileSnapshot  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.utils.rate_limiter import reset_rate_limiter  # noqa: E402

# 写请求统一携带的 CSRF 头（axios 前端侧自动注入，测试侧复现同一契约）
CSRF_HEADER = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture(scope="session", autouse=True)
def client():
    """session 级 TestClient：任何测试跑之前先触发 lifespan（建表+种子），
    纯函数级单测（工具/引擎）也依赖种子数据与表结构。"""
    if TEST_DB.exists():
        TEST_DB.unlink()
    with TestClient(app) as c:
        yield c
    reset_rate_limiter()


@pytest.fixture()
def db():
    """共享数据库会话（测试内直接操作数据用）。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def set_magic_mime():
    """切换 fake magic 返回的 MIME（测 MIME 校验/503 分支），用后自动还原。"""
    saved = _MAGIC_STATE["mime"]

    def _set(mime: str) -> None:
        _MAGIC_STATE["mime"] = mime

    yield _set
    _MAGIC_STATE["mime"] = saved


@pytest.fixture()
def make_user(db):
    """创建指定角色用户（默认已改密、固定口令 TestPass123），测试后清理。"""
    created = []

    def _make(role: UserRole = UserRole.STUDENT, password_changed: bool = True,
              tutor_id: int | None = None, name: str | None = None) -> User:
        uname = f"{role.value}_{uuid.uuid4().hex[:8]}"
        u = User(
            username=uname,
            password_hash=hash_password("TestPass123"),
            name=name or f"测试用户{uname[-4:]}",
            role=role,
            tutor_id=tutor_id,
            password_changed=password_changed,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        created.append(u)
        return u

    yield _make
    # 级联清理：先删关联数据（通知/会话/危机/画像），否则 User 删除时
    # ORM 尝试将子表 FK 置 NULL 触发 NOT NULL 约束失败，且残留画像
    # 会因 sqlite 主键复用污染后续用例。
    for u in created:
        u = db.get(User, u.id)
        if u:
            db.query(Notification).filter(Notification.user_id == u.id).delete()
            db.query(Feedback).filter(Feedback.user_id == u.id).delete()
            db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id.in_(
                    db.query(Conversation.id).filter(Conversation.user_id == u.id)
                )
            ).delete(synchronize_session=False)
            db.query(Conversation).filter(Conversation.user_id == u.id).delete()
            db.query(AIDialogSummary).filter(AIDialogSummary.student_id == u.id).delete()
            db.query(StudentProfileSnapshot).filter(
                StudentProfileSnapshot.student_id == u.id
            ).delete()
            db.delete(u)
    db.commit()


@pytest.fixture()
def login_token(client, make_user):
    """创建已改密用户并登录，返回 {user, token, headers}。"""

    def _make(role: UserRole = UserRole.STUDENT) -> dict:
        user = make_user(role=role)
        resp = client.post(
            "/api/auth/login",
            json={"username": user.username, "password": "TestPass123"},
            headers=CSRF_HEADER,
        )
        assert resp.status_code == 200, f"登录失败: {resp.text}"
        token = resp.json()["access_token"]
        return {
            "user": user,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    return _make


@pytest.fixture()
def seed_login(client):
    """登录 seed 内置账号（密码 123456/admin123），返回 Bearer 头。"""

    def _make(username: str = "2024001", password: str = "123456") -> dict:
        resp = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers=CSRF_HEADER,
        )
        assert resp.status_code == 200, f"登录失败: {resp.text}"
        token = resp.json()["access_token"]
        return {"token": token, "headers": {"Authorization": f"Bearer {token}"}}

    return _make


@pytest.fixture()
def api(client):
    """写请求自动附加 CSRF 头，规避共享 cookie jar 触发的 CSRF 拦截。"""

    class Api:
        @staticmethod
        def _merge(headers):
            h = dict(CSRF_HEADER)
            if headers:
                h.update(headers)
            return h

        def post(self, path, json=None, headers=None, files=None, data=None):
            return client.post(
                path, json=json, headers=self._merge(headers), files=files, data=data
            )

        def put(self, path, json=None, headers=None, files=None, data=None):
            return client.put(
                path, json=json, headers=self._merge(headers), files=files, data=data
            )

        def delete(self, path, headers=None):
            return client.delete(path, headers=self._merge(headers))

        def get(self, path, headers=None):
            return client.get(path, headers=headers)

    return Api()


@pytest.fixture(autouse=True)
def _per_test_reset(client):
    """每个用例前清空限流桶与共享 cookie jar。

    关键：client 为 session 级共享，前一用例登录（seed_login/login_token）
    留下的 campus_token 会让后续未带 Authorization 的用例以他人身份执行，
    产生 401/403 误判；限流桶同样需要跨用例隔离。
    """
    client.cookies.clear()
    reset_rate_limiter()
    yield
    client.cookies.clear()
    reset_rate_limiter()
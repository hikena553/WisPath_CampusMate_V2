"""文件下载鉴权（S4）：登录必需/分类白名单/路径穿越拦截/旧 URL 兼容。"""
from pathlib import Path

from app.api.files import resolve_safe
from app.api.files import UPLOAD_DIR


def test_download_requires_auth(client):
    resp = client.get("/api/files/root/demo.png")
    assert resp.status_code == 401


def test_branding_download_is_public(client):
    """品牌素材（站点 Logo/吉祥物）为公开资源：登录页未登录也要能渲染。"""
    target = UPLOAD_DIR / "branding" / "public_brand.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"BRANDPNG-789")
    try:
        resp = client.get("/api/files/branding/public_brand.png")
        assert resp.status_code == 200
        assert resp.content == b"BRANDPNG-789"
    finally:
        target.unlink(missing_ok=True)


def test_download_unknown_category(client, login_token):
    auth = login_token()
    resp = client.get("/api/files/no_such_cat/x.png", headers=auth["headers"])
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文件不存在"


def test_download_file_not_found(client, login_token):
    auth = login_token()
    resp = client.get("/api/files/root/ghost_1.png", headers=auth["headers"])
    assert resp.status_code == 404


def test_download_success(client, login_token):
    """真实文件可下载且内容一致。"""
    target = UPLOAD_DIR / "branding" / "logo_test.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"PNGDATA-123")
    try:
        auth = login_token()
        resp = client.get("/api/files/branding/logo_test.png", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.content == b"PNGDATA-123"
    finally:
        target.unlink(missing_ok=True)


def test_resolve_safe_blocks_traversal():
    """resolve_safe 拒绝绝对路径 / .. 穿越 / 空路径，且前缀校验兜底。"""
    assert resolve_safe("") is None
    assert resolve_safe("/etc/passwd") is None
    assert resolve_safe("..\\..\\secret.txt") is None
    assert resolve_safe("a/../../secret.txt") is None
    # 合法相对路径但文件不存在 → None（不泄露存在性之外信息）
    assert resolve_safe("not_exists_1.txt") is None
    # 穿透子目录逃逸到根外 → None（如 ../../users.db）
    assert resolve_safe("../users.db", "documents") is None


def test_legacy_uploads_route_requires_auth_and_works(client, login_token):
    target = UPLOAD_DIR / "legacy_demo.bmp"
    target.write_bytes(b"BMPDATA-456")
    try:
        # 未登录 → 401
        resp = client.get("/uploads/legacy_demo.bmp")
        assert resp.status_code == 401
        # 登录后旧 URL 兼容
        auth = login_token()
        resp = client.get("/uploads/legacy_demo.bmp", headers=auth["headers"])
        assert resp.status_code == 200
        assert resp.content == b"BMPDATA-456"
    finally:
        target.unlink(missing_ok=True)


def test_legacy_uploads_traversal_blocked(client, login_token):
    auth = login_token()
    resp = client.get("/uploads/..%2F..%2Ftest.db", headers=auth["headers"])
    assert resp.status_code == 404
"""上传校验测试：类型白名单/MIME 嗅探硬校验/压缩包安全/服务降级 503。"""
import io
import sys
import zipfile

from app.api.upload import UPLOAD_DIR


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_upload_requires_auth(client):
    resp = client.post("/api/upload", files={"file": ("a.png", _png_bytes(), "image/png")})
    assert resp.status_code == 401


def test_upload_bad_extension(api, login_token):
    auth = login_token()
    resp = api.post("/api/upload",
                    files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
                    headers=auth["headers"])
    assert resp.status_code == 400
    assert resp.json()["detail"] == "不支持的文件类型: .exe"


def test_upload_extension_required(api, login_token):
    auth = login_token()
    resp = api.post("/api/upload",
                    files={"file": ("noext", b"data", "application/octet-stream")},
                    headers=auth["headers"])
    assert resp.status_code == 400
    assert resp.json()["detail"] == "不支持的文件类型: "


def test_upload_mime_mismatch(api, login_token, set_magic_mime):
    """内容嗅探硬校验：伪装扩展名的 HTML 内容被拒。"""
    set_magic_mime("text/html")
    auth = login_token()
    resp = api.post("/api/upload",
                    files={"file": ("fake.png", b"<script>alert(1)</script>", "image/png")},
                    headers=auth["headers"])
    assert resp.status_code == 400
    assert "文件内容类型不匹配: text/html" in resp.json()["detail"]


def test_upload_magic_unavailable_returns_503(api, login_token, monkeypatch):
    """magic 缺失时拒绝上传（不允许静默跳过校验），503 提示稍后重试。"""
    monkeypatch.setitem(sys.modules, "magic", None)
    auth = login_token()
    resp = api.post("/api/upload",
                    files={"file": ("a.png", _png_bytes(), "image/png")},
                    headers=auth["headers"])
    assert resp.status_code == 503
    assert resp.json()["detail"] == "文件校验服务不可用，请稍后重试"


def test_upload_success_returns_url(api, login_token):
    auth = login_token()
    payload = _png_bytes()
    resp = api.post("/api/upload",
                    files={"file": ("report.png", payload, "image/png")},
                    headers=auth["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "report.png"
    assert body["url"].startswith("/api/files/root/report_")
    save_name = body["url"].rsplit("/", 1)[-1]
    saved = UPLOAD_DIR / save_name
    try:
        assert saved.is_file()
        assert saved.read_bytes() == payload
    finally:
        saved.unlink(missing_ok=True)


def _zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)
    return buf.getvalue()


def test_upload_zip_traversal_rejected(api, login_token, set_magic_mime):
    """压缩包内 ../ 路径穿越 → 拒绝。"""
    set_magic_mime("application/zip")
    auth = login_token()
    evil = _zip_bytes([("evil/../../etc/passwd", b"root")])
    resp = api.post("/api/upload",
                    files={"file": ("doc.zip", evil, "application/zip")},
                    headers=auth["headers"])
    assert resp.status_code == 400
    assert resp.json()["detail"] == "压缩包包含非法路径，已拒绝"


def test_upload_zip_too_many_members_rejected(api, login_token, set_magic_mime):
    """压缩包成员数超过 200 → 拒绝（防 zip 炸弹）。"""
    set_magic_mime("application/zip")
    auth = login_token()
    many = _zip_bytes([(f"f{i}.txt", b"1") for i in range(201)])
    resp = api.post("/api/upload",
                    files={"file": ("big.zip", many, "application/zip")},
                    headers=auth["headers"])
    assert resp.status_code == 400
    assert resp.json()["detail"] == f"压缩包内文件数超过限制（最多 200 个）"


def test_upload_zip_corrupt_rejected(api, login_token, set_magic_mime):
    """损坏的 zip（PK 头但无有效结构）→ 400 格式损坏。"""
    set_magic_mime("application/zip")
    auth = login_token()
    resp = api.post("/api/upload",
                    files={"file": ("bad.zip", b"PK\x03\x04" + b"\x00" * 200, "application/zip")},
                    headers=auth["headers"])
    assert resp.status_code == 400
    assert resp.json()["detail"] == "压缩包格式损坏"


def test_upload_valid_zip_accepted(api, login_token, set_magic_mime):
    """正常 zip 通过全部校验并入库。"""
    set_magic_mime("application/zip")
    auth = login_token()
    good = _zip_bytes([("readme.txt", b"hello")])
    resp = api.post("/api/upload",
                    files={"file": ("docs.zip", good, "application/zip")},
                    headers=auth["headers"])
    assert resp.status_code == 200
    save_name = resp.json()["url"].rsplit("/", 1)[-1]
    (UPLOAD_DIR / save_name).unlink(missing_ok=True)
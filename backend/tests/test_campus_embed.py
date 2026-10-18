"""原页渲染反代（campus_embed）：base 注入、编码统一、桥接协议与可嵌入性验证。

全部 monkeypatch ``fetch_html``，不触网；只验证「我们自己产出的响应」。

注：这里的断言对齐 campus_embed 模块的**实际契约**——
- 链接重写不是在后端做字符串替换，而是注入 ``<base>`` + 桥接脚本，
  由脚本拦截页内点击（发 ``navigate`` 消息）交给父页面在阅读器里跳转；
- ``BRIDGE_SOURCE == "campus-reader"``（与前端 ArticleReader 监听的 source 一致）。
"""
import httpx
from fastapi.testclient import TestClient  # noqa: F401  (类型提示用)

from app.api import campus as campus_api
from app.services import campus_embed

SAMPLE_HTML = """<html><head><meta http-equiv="Content-Type" content="text/html; charset=gb2312">
<title>关于某某工作的通知</title><link rel="stylesheet" href="/css/main.css"></head>
<body>
  <a href="/info/1012/2.htm">站内下一条</a>
  <a href="https://jwc.mycc.edu.cn/info/1012/3.htm">站内绝对链接</a>
  <a href="https://www.moe.gov.cn/xxx.htm">教育部</a>
  <a href="javascript:void(0)">忽略</a>
  <img src="../__local/a.png">
  <form action="/search.htm" method="post"><input name="q"></form>
</body></html>"""

TARGET = "https://jwc.mycc.edu.cn/info/1012/1.htm"


def _fake_fetch(html: str = SAMPLE_HTML):
    # 与 article_reader.fetch_html 契约一致：(最终 URL, HTML 文本)。
    # 这里最终 URL 用原地址，模拟「无重定向」的常规抓取。
    return lambda url: (url, html)


def test_build_embed_html_injects_base_and_bridge(monkeypatch):
    """注入 base 指向源站、补 viewport、去掉旧 charset 声明、挂上桥接脚本。"""
    monkeypatch.setattr(campus_embed, "fetch_html", _fake_fetch())

    out = campus_embed.build_embed_html(TARGET, "http://127.0.0.1:8000/")

    # 相对资源（../__local/a.png、/css/main.css）靠 <base> 回源站解析
    assert '<base href="https://jwc.mycc.edu.cn/info/1012/"/>' in out
    # 学校老站的 gb2312 声明会被去掉，内容统一按 UTF-8 呈现
    assert "gb2312" not in out
    # 移动端视口：避免 iframe 内按桌面宽度缩放
    assert 'name="viewport"' in out
    # 桥接脚本：source 与前端 ArticleReader 监听的一致，走 postMessage
    assert campus_embed.BRIDGE_SOURCE == "campus-reader"
    assert "campus-reader" in out and "postMessage" in out
    for kind in ("ready", "navigate", "error"):
        assert f"'{kind}'" in out


def test_build_embed_html_keeps_original_markup(monkeypatch):
    """后端不做链接重写：站内/站外地址都按原样保留，跳转交给桥接脚本判定。"""
    monkeypatch.setattr(campus_embed, "fetch_html", _fake_fetch())

    out = campus_embed.build_embed_html(TARGET, "http://127.0.0.1:8000/")

    assert 'href="/info/1012/2.htm"' in out
    assert 'href="https://jwc.mycc.edu.cn/info/1012/3.htm"' in out
    assert 'href="https://www.moe.gov.cn/xxx.htm"' in out
    # javascript: 伪链接不动（脚本里按前缀跳过）
    assert 'href="javascript:void(0)"' in out
    # 代理不转发 POST，表单保持原 action 由脚本/浏览器处理，后端不改写
    assert 'action="/search.htm"' in out


def test_build_embed_html_strips_frame_blocking_meta(monkeypatch):
    """源页自带的 CSP / X-Frame-Options / refresh meta 必须摘掉，否则嵌不进去。"""
    html = SAMPLE_HTML.replace(
        "<title>",
        '<meta http-equiv="X-Frame-Options" content="SAMEORIGIN">'
        '<meta http-equiv="Content-Security-Policy" content="frame-ancestors \'self\'">'
        "<title>",
    )
    monkeypatch.setattr(campus_embed, "fetch_html", _fake_fetch(html))

    out = campus_embed.build_embed_html(TARGET, "http://127.0.0.1:8000/")

    lowered = out.lower()
    assert "x-frame-options" not in lowered
    assert "frame-ancestors" not in lowered


def test_build_embed_html_rejects_foreign_url():
    """白名单外地址直接拒绝，不触网。"""
    try:
        campus_embed.build_embed_html("https://evil.example.com/x.htm", "http://127.0.0.1:8000/")
    except PermissionError:
        return
    raise AssertionError("站外地址应当被拒绝")


def test_embed_endpoint_is_frameable(client, monkeypatch):
    """接口产出：200 HTML、**不带 X-Frame-Options**（否则应用内 iframe 嵌不进来）。"""
    monkeypatch.setattr(campus_embed, "fetch_html", _fake_fetch())

    resp = client.get("/api/campus/embed", params={"url": TARGET})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "x-frame-options" not in {k.lower() for k in resp.headers}
    assert "<base href=" in resp.text and "campus-reader" in resp.text


def test_embed_response_sets_hardening_csp(client, monkeypatch):
    """反代页跑的是学校站点的全部脚本（含内联），来源是我们自己的源。

    sandbox（不含 allow-same-origin）挡住「读应用数据」，但挡不住「脚本能发请求/弹窗」，
    因此响应必须带 CSP 收口：object-src/base-uri 关死、frame-ancestors 只允许自嵌。
    script-src 必须保留 'unsafe-inline' 'unsafe-eval'，否则学校页会直接白屏。
    """
    monkeypatch.setattr(campus_embed, "fetch_html", _fake_fetch())

    resp = client.get("/api/campus/embed", params={"url": TARGET})
    csp = resp.headers.get("content-security-policy") or ""

    assert csp, "反代响应必须带 CSP"
    assert "object-src 'none'" in csp
    assert "base-uri 'none'" in csp
    assert "frame-ancestors 'self'" in csp
    # 学校页依赖内联脚本与动态求值，收紧即白屏
    assert "'unsafe-inline'" in csp and "'unsafe-eval'" in csp


def test_embed_endpoint_reports_fetch_failure(client, monkeypatch):
    """源站抓不到时返回 502 + 可读错误页（不是 JSON），前端据此回落到纯净正文。"""

    def boom(url):
        raise RuntimeError("源站返回 404")

    monkeypatch.setattr(campus_embed, "fetch_html", boom)
    resp = client.get("/api/campus/embed", params={"url": TARGET})

    assert resp.status_code == 502
    assert resp.headers["content-type"].startswith("text/html")
    assert "页面抓取失败" in resp.text
    # 错误页同样不带 X-Frame-Options，且要能被嵌入
    assert "x-frame-options" not in {k.lower() for k in resp.headers}
    # 错误页也带桥接脚本：iframe 里的父页面能据此切到自己的错误态
    assert "页面暂不可用" in resp.text
    assert "campus-reader" in resp.text and "postMessage" in resp.text


def test_embed_error_page_rejected_by_whitelist(client):
    """白名单外的地址在进入抓取前就被拒（400 JSON，而不是 502 错误页）。"""
    resp = client.get("/api/campus/embed", params={"url": "https://evil.example.com/x.htm"})
    assert resp.status_code == 400


def test_build_embed_error_html_escapes_message():
    """错误页：原因里的 HTML 标签要被剥掉，不能原样落到响应里。"""
    out = campus_embed.build_embed_error_html(
        "https://jwc.mycc.edu.cn/a.htm?x=1&y=2", '抓取失败："引号" & <标签>'
    )
    assert "<标签>" not in out
    assert "页面暂不可用" in out
    assert "campus-reader" in out


def test_bridge_script_embeds_page_url():
    """桥接脚本要带上真实页面地址，父页面靠它实现返回/前进与地址栏。"""
    script = campus_embed._bridge_script("https://jwc.mycc.edu.cn/a.htm?x=1&y=2")
    assert "https://jwc.mycc.edu.cn/a.htm?x=1&y=2" in script
    # JSON 编码后进入脚本，引号不会截断字符串
    assert "'x=1&y=2'" in script or '"https://jwc.mycc.edu.cn/a.htm?x=1&y=2"' in script


def test_reader_reports_supports_original(client, seed_login, monkeypatch):
    """纯净正文接口按站点回报 supports_original，前端据此决定是否给「原页」入口。"""
    monkeypatch.setattr(
        campus_api, "read_url",
        lambda url: {
            "kind": "links", "title": "T", "date": None,
            "content_html": "", "links": [], "source_url": url,
        },
    )
    headers = seed_login()["headers"]

    static_page = client.get("/api/campus/reader", params={"url": TARGET}, headers=headers)
    assert static_page.status_code == 200
    assert static_page.json()["supports_original"] is True

    spa_page = client.get(
        "/api/campus/reader", params={"url": "https://lib.mycc.edu.cn/"}, headers=headers
    )
    assert spa_page.status_code == 200
    assert spa_page.json()["supports_original"] is False


def test_reader_rejects_foreign_url(client, seed_login):
    """白名单外地址在进入抓取前就被拒（不打到 read_url）。"""
    resp = client.get(
        "/api/campus/reader",
        params={"url": "https://evil.example.com/x.htm"},
        headers=seed_login()["headers"],
    )
    assert resp.status_code == 400

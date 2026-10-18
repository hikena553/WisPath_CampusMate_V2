"""绵城印象爬虫：图书馆站可达性预检、DoH 兜底、失败冷却与入口过滤（全部 monkeypatch，不触网）。"""
import time

import httpx

from app.services import impression_crawler as ic
from app.utils.announcement_parser import AnnouncementItem


class _FakeResponse:
    """仅实现 .json() 的最小响应替身（DoH 查询用）。"""

    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _transport_error(url: str) -> httpx.ConnectError:
    """模拟本地 DNS 解析失败的传输层异常。"""
    return httpx.ConnectError("name resolution failed", request=httpx.Request("GET", url))


def _is_doh(url: str) -> bool:
    return any(ep in url for ep in ic.LIBRARY_DOH_ENDPOINTS)


def test_library_preflight_falls_back_to_doh_ip(monkeypatch):
    """本地 DNS 解析不了图书馆域名时，用 DoH 拿到的 IP 给 Chromium 做域名映射。

    图书馆站（超星托管）公网可解析、校内/本地 DNS 可能不回；映射后浏览器仍以
    原域名发起请求（SNI/Host 不变），证书校验不受影响。
    """

    def fake_get(url, **kwargs):
        if _is_doh(url):
            # 真实返回：CNAME + A 记录混排，应挑出第一个 IPv4
            return _FakeResponse(
                {"Answer": [{"data": "4ns3v544.mh.chaoxing.com."}, {"data": "203.0.113.7"}]}
            )
        raise _transport_error(url)

    monkeypatch.setattr(ic.httpx, "get", fake_get)
    host = ic.urlparse(ic.LIBRARY_URL).hostname
    assert ic._library_launch_args() == [f"--host-resolver-rules=MAP {host} 203.0.113.7"]


def test_library_preflight_returns_empty_args_when_reachable(monkeypatch):
    """站点直连正常时不需要任何额外启动参数。"""

    def fake_get(url, **kwargs):
        return _FakeResponse({"Answer": []})

    monkeypatch.setattr(ic.httpx, "get", fake_get)
    assert ic._library_launch_args() == []


def test_library_preflight_skips_when_unreachable(monkeypatch):
    """站点与 DoH 都不可用 → None：本轮直接跳过，不再白等 Playwright 超时。"""

    def fake_get(url, **kwargs):
        raise _transport_error(url)

    monkeypatch.setattr(ic.httpx, "get", fake_get)
    assert ic._library_launch_args() is None


def test_library_unreachable_sets_cooldown(monkeypatch):
    """不可达后进入冷却：冷却期内直接短路，避免每轮都重试并刷告警。"""
    monkeypatch.setattr(ic, "_library_launch_args", lambda: None)
    monkeypatch.setattr(ic, "_library_unreachable_until", 0.0)

    assert ic._library_news_via_playwright() == []
    assert ic._library_unreachable_until > time.time()

    def boom():
        raise AssertionError("冷却期内不应再探测图书馆站")

    monkeypatch.setattr(ic, "_library_launch_args", boom)
    assert ic._library_news_via_playwright() == []


def test_fetch_jwc_entries_hides_tool_pages(monkeypatch):
    """课表查询 / 教学校历 / 作息时间 不再出现在“教务系统入口”网格里。

    标题与链接双重过滤：学校改文案后按链接仍能命中，避免下轮抓取又冒出来。
    """
    parsed = [
        AnnouncementItem(title="教务管理系统", url="https://jwgl.mycc.edu.cn"),
        AnnouncementItem(title="课表查询", url="https://jwc.mycc.edu.cn/jwgl/kbcx.htm"),
        AnnouncementItem(title="教学校历", url="https://jwc.mycc.edu.cn/jwgl/jxxl.htm"),
        AnnouncementItem(title="作息时间", url="https://jwc.mycc.edu.cn/jwgl/zxsj.htm"),
        # 改标题但链接不变，仍应被过滤
        AnnouncementItem(title="作息时间表（新）", url="https://jwc.mycc.edu.cn/jwgl/zxsj.htm/"),
        AnnouncementItem(title="实验管理平台", url="https://syglxt.mycc.edu.cn/zxcas"),
        AnnouncementItem(title="超星在线学习平台", url="https://44oldowe.mh.chaoxing.com/page/1164017/show"),
    ]
    monkeypatch.setattr(ic, "_get", lambda url, timeout=10: "")
    monkeypatch.setattr(ic, "parse_system_entries", lambda html, **kwargs: list(parsed))

    items = ic.fetch_jwc_entries()
    assert [it.title for it in items] == ["教务管理系统", "实验管理平台", "超星在线学习平台"]
    assert all(it.source == "jwc_entries" for it in items)
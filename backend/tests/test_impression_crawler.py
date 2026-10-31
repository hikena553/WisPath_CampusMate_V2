"""绵城印象爬虫：教务系统入口过滤（全部 monkeypatch，不触网）。"""
from app.services import impression_crawler as ic
from app.utils.announcement_parser import AnnouncementItem


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

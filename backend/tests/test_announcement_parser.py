import pytest
from app.utils.announcement_parser import (
    AnnouncementItem,
    parse_system_entries,
    parse_news_list,
    parse_detail_first_image,
    parse_college_news,
)

JXDT_HTML = """
<ul>
  <li><a href="../info/1012/3831.htm"><div class="date-t"><span>31</span><p>2026-07</p></div>
    <h3>师生卫冕全国健身气功锦标赛两项冠军</h3></a></li>
  <li><a href="../info/1012/3822.htm"><div class="date-t"><span>17</span><p>2026-07</p></div>
    <h3>基层教学管理人员能力提升培训圆满举行</h3></a></li>
</ul>
"""

TZGG_HTML = """
<ul>
  <li><a href="../info/1011/3841.htm"><span>08-01</span><i>2026</i>
    <h3>关于2026-2027学年第一学期学生教材订购的通知</h3></a></li>
</ul>
"""

GJXX_HTML = """
<ul>
  <li><a href="https://www.sceea.cn/Html/202411/Newsdetail_3985.html">
    <h3>四川省2025年专升本考试招生工作实施规定</h3><p>2024-11-15</p></a></li>
</ul>
"""

ENTRIES_HTML = """
<div class="function-icons">
  <a class="icon-item" href="https://jwgl.mycc.edu.cn"><p>教务管理系统</p></a>
  <a class="icon-item" href="https://xixunyun.com/login.html"><p>实习管理系统</p></a>
</div>
"""

DETAIL_HTML = """
<html><body>
<header><img src="../../images/logo.png"></header>
<div class="content"><img src="/__local/8/A6/29/XXXX.png"><p>正文</p></div>
</body></html>
"""

COLLEGE_HTML = """
<div><ul>
  <li><a href="info/1008/2402.htm">人工智能学院女教师赴北川开展活动 <span>2026.04.01</span></a></li>
  <li><a href="info/1008/2623.htm">斩获国赛二等奖！我校学子获奖</a></li>
  <li><a href="info/1008/2617.htm">心系留校奋斗学子 <span>2026.07.15</span></a></li>
</ul></div>
"""


class TestParseSystemEntries:
    def test_parses_icon_items(self):
        items = parse_system_entries(ENTRIES_HTML, base_url="https://jwc.mycc.edu.cn")
        assert len(items) == 2
        assert items[0].title == "教务管理系统"
        assert items[0].url == "https://jwgl.mycc.edu.cn"


class TestParseNewsList:
    def test_parses_jxdt_date_split(self):
        items = parse_news_list(JXDT_HTML, base_url="https://jwc.mycc.edu.cn", url_marker="info/1012/")
        assert len(items) == 2
        assert items[0].title == "师生卫冕全国健身气功锦标赛两项冠军"
        assert items[0].date == "2026-07-31"
        assert items[0].url == "https://jwc.mycc.edu.cn/info/1012/3831.htm"

    def test_parses_tzgg_full_date(self):
        items = parse_news_list(TZGG_HTML, base_url="https://jwc.mycc.edu.cn", url_marker="info/1011/")
        assert len(items) == 1
        assert items[0].date == "2026-08-01"

    def test_parses_gjxx_external_date(self):
        items = parse_news_list(GJXX_HTML, base_url="https://jwc.mycc.edu.cn", url_marker=None)
        assert len(items) == 1
        assert items[0].date == "2024-11-15"
        assert items[0].url.startswith("https://www.sceea.cn")


class TestParseDetailFirstImage:
    def test_extracts_local_image(self):
        url = parse_detail_first_image(DETAIL_HTML, base_url="https://jwc.mycc.edu.cn")
        assert url == "https://jwc.mycc.edu.cn/__local/8/A6/29/XXXX.png"

    def test_returns_none_when_no_image(self):
        assert parse_detail_first_image("<html><body>无图</body></html>", base_url="x") is None


class TestParseCollegeNews:
    def test_extracts_titles_with_dates(self):
        items = parse_college_news(COLLEGE_HTML, college_key="AI", base_url="https://xdjsxy.mycc.edu.cn")
        assert len(items) == 3
        assert items[0].college_key == "AI"
        assert items[0].title.startswith("人工智能学院女教师")
        assert items[0].date == "2026.04.01"
        assert items[0].url == "https://xdjsxy.mycc.edu.cn/info/1008/2402.htm"

    def test_titles_without_date_have_none(self):
        items = parse_college_news(COLLEGE_HTML, college_key="AI", base_url="x")
        assert items[1].date is None

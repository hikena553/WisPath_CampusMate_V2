"""学院首页新闻解析：标题污染清洗 + 日期规范化（全部内联 HTML，不联网）。"""
import pytest

from app.utils.announcement_parser import parse_college_news

BASE = "https://mksxy.mycc.edu.cn/"


# ── 1. 长标题污染（真实结构：a 内 h3=标题 + p=摘要正文） ──────────────────
POLLUTED_HTML = """
<html><body>
<div class="wac">
  <a href="info/1003/2794.htm">
    <h3>喜报！我校马克思主义学院师生团队荣获四川省首届新时代全景资源创意展示大赛一等奖</h3>
    <p>近日，由四川省教育厅指导，教育部全国高校思政课虚拟仿真体验教学中心、四川省高校思想政治工作研究会思政课研究分会主办的“长征精神·薪火相传”大赛评审结果公布。我校马克思主义学院师生团队荣获一等奖。</p>
  </a>
</div>
</body></html>
"""


def test_polluted_title_uses_h3_not_whole_anchor_text():
    """a 内同时含 h3(标题) 与 p(摘要) 时，标题只取 h3，不被正文污染。

    这是 123 字污染的根因：学院首页 <a> 把标题和摘要包在一起。
    """
    items = parse_college_news(POLLUTED_HTML, "马克思主义学院", BASE)
    assert len(items) == 1
    title = items[0].title
    assert title == "喜报！我校马克思主义学院师生团队荣获四川省首届新时代全景资源创意展示大赛一等奖"
    assert len(title) <= 40
    # 正文摘要不应出现在标题里
    assert "近日" not in title
    assert "四川省教育厅指导" not in title
    assert "评审结果公布" not in title


def test_title_never_exceeds_limit_and_is_truncated_with_ellipsis():
    """退化场景（无结构化子节点）：超长标题必须被截断并以 … 收尾。"""
    long_text = "关于组织开展2026年秋季学期学生综合素质测评及奖学金评定工作的通知" * 3
    html = f'<html><body><ul><li><a href="info/1003/9999.htm">{long_text}</a></li></ul></body></html>'
    items = parse_college_news(html, "商学院", BASE)
    assert len(items) == 1
    title = items[0].title
    assert len(title) <= 40
    assert title.endswith("…")


def test_normal_short_title_not_broken():
    """正常短标题必须原样保留：不截断、不加省略号、不丢字。"""
    html = """
    <html><body><ul>
      <li><a href="info/1045/2405.htm">学院开展9月专项安全检查</a></li>
      <li><a href="info/1045/2415.htm">学院开展庆祝第42个教师节系列活动</a></li>
    </ul></body></html>
    """
    items = parse_college_news(html, "健康与教育学院", BASE)
    assert [it.title for it in items] == [
        "学院开展9月专项安全检查",
        "学院开展庆祝第42个教师节系列活动",
    ]


def test_long_but_complete_title_kept_when_under_limit():
    """本身较长（≤40 字）的正常标题不应被误伤。"""
    title = "商学院教师在2026年全国商科教育教学成果认定中斩获一等奖、二等奖"
    assert len(title) == 33
    html = f'<html><body><li><a href="info/1224/5275.htm">{title}</a></li></body></html>'
    items = parse_college_news(html, "商学院", BASE)
    assert items[0].title == title


def test_trailing_site_ellipsis_stripped():
    """站点 CSS 自带的截断残留 "..." / "…" 要剥离。"""
    html = """
    <html><body><ul>
      <li><a href="info/1003/2794.htm">喜报！我校马克思主义学院师生团队荣获四川省首...</a></li>
      <li><a href="info/1003/2824.htm">教研携手谋发展 结对共建育新人——西南科技大学…</a></li>
    </ul></body></html>
    """
    items = parse_college_news(html, "马克思主义学院", BASE)
    assert items[0].title == "喜报！我校马克思主义学院师生团队荣获四川省首"
    assert items[1].title == "教研携手谋发展 结对共建育新人——西南科技大学"
    assert all(not it.title.endswith(("...", "…", "。")) for it in items)


# ── 2. 日期：点号 / 短横 / 兄弟节点 / 缺失 ────────────────────────────────
def test_dotted_date_normalized_to_iso():
    """点号日期 2026.04.01 → 2026-04-01（人工智能学院真实格式）。"""
    html = """
    <html><body><ul>
      <li><a href="info/1008/2402.htm"><span>人工智能学院女教师赴北川开展“三八”活动</span><span>2026.04.01</span></a></li>
    </ul></body></html>
    """
    items = parse_college_news(html, "人工智能学院", BASE)
    assert len(items) == 1
    assert items[0].date == "2026-04-01"
    assert "2026" not in items[0].title


def test_dash_date_normalized_to_iso():
    """短横日期保持 ISO 格式（创意设计学院真实格式）。"""
    html = """
    <html><body><ul>
      <li><a href="info/1021/1966.htm"><span>走进智能产线，读懂中国智造</span><span>2026-10-15</span></a></li>
    </ul></body></html>
    """
    items = parse_college_news(html, "创意设计学院", BASE)
    assert items[0].date == "2026-10-15"
    assert items[0].title == "走进智能产线，读懂中国智造"


def test_date_from_sibling_node_outside_anchor():
    """日期在 a 外的兄弟节点：<p class="section2-Body-Date">（健康与教育学院真实结构）。"""
    html = """
    <html><body><ul>
      <li class="section2-BodyslickItem">
        <a href="info/1045/2406.htm">学院开展庆祝第42个教师节系列活动</a>
        <p class="section2-Body-Date">2026-09-24</p>
      </li>
    </ul></body></html>
    """
    items = parse_college_news(html, "健康与教育学院", BASE)
    assert items[0].date == "2026-09-24"
    assert items[0].title == "学院开展庆祝第42个教师节系列活动"


def test_duplicate_url_second_occurrence_enriches_date():
    """同一 URL 渲染两次时，用后出现的带日期条目补齐先出现的无日期条目。

    健康与教育学院真实页面：同一个新闻先出现在轮播展示位（标题无日期），
    再出现在列表位（标题 + 日期）。旧实现按 url 去重直接丢弃后者，导致日期永远取不到。
    """
    html = """
    <html><body>
      <div class="slick"><a href="info/1045/2406.htm">学院开展庆祝第42个教师节系列活动</a></div>
      <ul>
        <li class="section2-BodyslickItem">
          <a href="info/1045/2406.htm">学院开展庆祝第42个教师节系列活动</a>
          <p class="section2-Body-Date">2026-09-24</p>
        </li>
      </ul>
    </body></html>
    """
    items = parse_college_news(html, "健康与教育学院", BASE)
    assert len(items) == 1
    assert items[0].title == "学院开展庆祝第42个教师节系列活动"
    assert items[0].date == "2026-09-24"


def test_date_year_month_and_day_split_across_nodes():
    """日与年-月分处两个节点（商学院真实结构：span.date=14 + span.year=2026-10）。"""
    html = """
    <html><body><ul class="label_list23_date">
      <li class="col-md-4">
        <div class="item">
          <div class="time"><span class="date">14</span><span class="year">2026-10</span></div>
          <div class="info"><h4 class="item-tit">
            <a href="info/1225/5301.htm">绵阳城市学院商学院关于2026年秋季学期教学安排的通知</a>
          </h4></div>
        </div>
      </li>
    </ul></body></html>
    """
    items = parse_college_news(html, "商学院", BASE)
    assert len(items) == 1
    assert items[0].date == "2026-10-14"


def test_date_month_day_and_year_split_across_nodes():
    """月-日与年份分处两个节点（智能制造与工程学院真实结构：h1=10-14 + div.nian=2026）。"""
    html = """
    <html><body><ul>
      <li>
        <div class="dat fl">
          <div class="tian"><h1 style="font-size:15px;">10-14</h1></div>
          <div class="nian" style="font-size:15px">2026</div>
        </div>
        <div class="tz_list fr">
          <a href="info/1049/2943.htm" title="关于绵阳城市学院2025-2026学年国家励志奖学金拟推荐名单公示的通知">关于绵阳城市学院2025-2026学年国家励志奖学...</a>
          <p>详细内容见附件</p>
        </div>
      </li>
    </ul></body></html>
    """
    items = parse_college_news(html, "智能制造与工程学院", BASE)
    assert len(items) == 1
    assert items[0].date == "2026-10-14"
    # a[title] 是未被 CSS 截断的完整标题，优先于可见文本
    assert items[0].title == "关于绵阳城市学院2025-2026学年国家励志奖学金拟推荐名单公示的通知"


def test_anchor_title_attribute_preferred_over_truncated_text():
    """a[title] 属性是完整标题，优先于被站点 CSS 截断的可见文本。"""
    html = """
    <html><body><li>
      <a href="info/1008/2402.htm" title="人工智能学院女教师赴北川开展“三八”节主题实践活动">
        人工智能学院女教师赴北川开展“三八”...
        <span class="date">2026.04.01</span>
      </a>
    </li></body></html>
    """
    items = parse_college_news(html, "人工智能学院", BASE)
    assert items[0].title == "人工智能学院女教师赴北川开展“三八”节主题实践活动"
    assert items[0].date == "2026-04-01"


def test_date_span_with_class_date_not_treated_as_title():
    """a 内只有 span.date 时，标题来自文本节点而非日期 span（人工智能学院真实结构）。"""
    html = """
    <html><body><li>
      <a href="info/1008/2402.htm">人工智能学院女教师赴北川开展“三八”...
        <span class="date">2026.04.01</span></a>
    </li></body></html>
    """
    items = parse_college_news(html, "人工智能学院", BASE)
    assert len(items) == 1
    assert items[0].title == "人工智能学院女教师赴北川开展“三八”"
    assert items[0].date == "2026-04-01"


def test_label_datatime_span_is_date_not_title():
    """创意设计学院：a > span(标题) + span.label_datatime(日期)。"""
    html = """
    <html><body><li>
      <a href="info/1021/1966.htm">
        <span>走进智能产线，读懂中国智造——</span>
        <span class="label_datatime">2026-10-15</span>
      </a>
    </li></body></html>
    """
    items = parse_college_news(html, "创意设计学院", BASE)
    assert items[0].title == "走进智能产线，读懂中国智造——"
    assert items[0].date == "2026-10-15"


def test_date_from_prev_sibling_span():
    """日期在 a 的前置兄弟 <span>（商学院真实结构）。"""
    html = """
    <html><body><ul>
      <li>
        <span class="label_datatime">10-13</span>
        <a href="info/1224/5302.htm">第九届全国高校企业价值创造实战竞赛校赛圆满落幕</a>
      </li>
    </ul></body></html>
    """
    items = parse_college_news(html, "商学院", BASE)
    assert items[0].title == "第九届全国高校企业价值创造实战竞赛校赛圆满落幕"
    # 只有 MM-DD 没有年份：不臆造年份，降级为 None
    assert items[0].date is None


def test_missing_date_stays_none():
    """页面确实没有日期时 date 为 None（前端降级处理），但标题仍要保留。"""
    html = """
    <html><body><ul>
      <li><a href="info/1011/1527.htm">大力弘扬教育家精神，共筑尊师重教风尚</a><span>09-14</span></li>
    </ul></body></html>
    """
    items = parse_college_news(html, "终身教育学院", BASE)
    assert len(items) == 1
    assert items[0].date is None
    assert items[0].title == "大力弘扬教育家精神，共筑尊师重教风尚"


def test_year_range_in_title_not_mistaken_for_date():
    """标题里的学年版权段 2025-2026 不是日期，不能被抽走。"""
    html = """
    <html><body><ul>
      <li><a href="info/1049/2932.htm">关于绵阳城市学院2025-2026学年国家奖学金拟推荐名单的公示</a></li>
    </ul></body></html>
    """
    items = parse_college_news(html, "智能制造与工程学院", BASE)
    assert items[0].date is None
    assert "2025-2026学年" in items[0].title


# ── 3. 通用契约 ──────────────────────────────────────────────────────────
def test_url_is_absolute_and_college_key_preserved():
    html = '<html><body><li><a href="info/1003/2794.htm">喜报！我校马克思主义学院师生团队荣获一等奖</a></li></body></html>'
    items = parse_college_news(html, "马克思主义学院", BASE)
    assert items[0].url == "https://mksxy.mycc.edu.cn/info/1003/2794.htm"
    assert items[0].college_key == "马克思主义学院"
    assert items[0].source is None  # source 由调用方设置


def test_image_only_anchor_skipped():
    """纯图片链接（无文本）不产生条目——严格保持既有行为。"""
    html = """
    <html><body>
      <li><a href="info/1003/2460.htm"><img src="a.jpg"></a></li>
      <li><a href="info/1003/2794.htm">喜报！我校马克思主义学院师生团队荣获一等奖</a></li>
    </body></html>
    """
    items = parse_college_news(html, "马克思主义学院", BASE)
    assert len(items) == 1
    assert items[0].title == "喜报！我校马克思主义学院师生团队荣获一等奖"


def test_duplicate_url_deduplicated():
    html = """
    <html><body>
      <li><a href="info/1003/2794.htm">喜报！我校马克思主义学院师生团队荣获一等奖</a></li>
      <li><a href="info/1003/2794.htm">喜报！我校马克思主义学院师生团队荣获一等奖</a></li>
    </body></html>
    """
    items = parse_college_news(html, "马克思主义学院", BASE)
    assert len(items) == 1


@pytest.mark.parametrize("placeholder", ["查看更多", "更多", "进入官网", "查看详情"])
def test_placeholder_links_skipped(placeholder):
    """占位链接不产生条目——严格保持既有行为。"""
    html = f'<html><body><li><a href="info/1051/1596.htm">{placeholder}</a></li></body></html>'
    assert parse_college_news(html, "创意设计学院", BASE) == []


def test_empty_html_returns_empty_list():
    assert parse_college_news("", "商学院", BASE) == []


def test_cleaned_empty_title_dropped_not_emitted_as_blank():
    """清洗后为空则丢弃该条，绝不产出空标题。"""
    html = """
    <html><body><ul>
      <li><a href="info/1224/9001.htm">......</a></li>
      <li><a href="info/1224/9002.htm">第九届全国高校企业价值创造实战竞赛校赛圆满落幕</a></li>
    </ul></body></html>
    """
    items = parse_college_news(html, "商学院", BASE)
    assert [it.title for it in items] == ["第九届全国高校企业价值创造实战竞赛校赛圆满落幕"]


def test_placeholder_prefix_with_trailing_bracket_skipped():
    """'了解详情 >' 这类带尾缀的占位链接要过滤（终身教育学院真实页面）。"""
    html = """
    <html><body>
      <div class="news-middle-top-btn"><a href="info/1011/1130.htm">了解详情 ></a></div>
      <li><a href="info/1011/1527.htm">大力弘扬教育家精神，共筑尊师重教风尚</a></li>
    </body></html>
    """
    items = parse_college_news(html, "终身教育学院", BASE)
    assert [it.title for it in items] == ["大力弘扬教育家精神，共筑尊师重教风尚"]
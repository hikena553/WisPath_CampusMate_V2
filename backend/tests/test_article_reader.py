"""站内文章阅读器（/api/campus/reader）单元测试：白名单校验 + 正文/链接提取 + 原页支持判定。"""
import pytest

from app.services.article_reader import extract_article, is_allowed_url, requires_js


ARTICLE_HTML = """
<html><head><title>测试文章标题-绵阳城市学院教务处</title></head>
<body>
<form name="_newscontent_fromname">
  <div class="art-tit cont-tit">
    <h3>测试文章标题</h3>
    <p><span>日期：2026-10-09</span></p>
  </div>
  <div class="art-body">
    <div id="vsb_content_6"><div class="v_news_content">
      <p>正文第一段，包含足够的文字长度以便被识别为有效内容区域。</p>
      <img src="/__local/a.png" width="800" />
      <a href="/info/1012/999.htm" onclick="hack()">站内链接</a>
      <script>alert(1)</script>
    </div></div>
  </div>
</form>
</body></html>
"""

LIST_HTML = """
<html><head><title>教学动态-绵阳城市学院教务处</title></head>
<body>
<ul class="news_list">
  <li><a href="/info/1012/101.htm" title="第一条新闻标题内容">第一条新闻标题内容</a><span>2026-10-01</span></li>
  <li><a href="/info/1012/102.htm" title="第二条新闻标题内容">第二条新闻标题内容</a><span>2026-09-20</span></li>
</ul>
</body></html>
"""


def test_whitelist():
    assert is_allowed_url("https://jwc.mycc.edu.cn/info/1012/1.htm")
    assert is_allowed_url("https://www.mycc.edu.cn/mcyx/")
    assert is_allowed_url("http://lib.mycc.edu.cn/")
    assert not is_allowed_url("https://evil.example.com/x.htm")
    assert not is_allowed_url("ftp://jwc.mycc.edu.cn/a.htm")
    assert not is_allowed_url("not-a-url")


def test_extract_article():
    data = extract_article(ARTICLE_HTML, "https://jwc.mycc.edu.cn/info/1012/3953.htm")
    assert data["kind"] == "article"
    assert data["title"] == "测试文章标题"
    assert data["date"] == "2026-10-09"
    html = data["content_html"]
    # 脚本与事件属性被剔除
    assert "<script" not in html and "onclick" not in html
    # 相对地址已绝对化
    assert 'src="https://jwc.mycc.edu.cn/__local/a.png"' in html
    assert 'href="https://jwc.mycc.edu.cn/info/1012/999.htm"' in html


def test_extract_links_fallback():
    data = extract_article(LIST_HTML, "https://jwc.mycc.edu.cn/jwgl/jxdt.htm")
    assert data["kind"] == "links"
    assert len(data["links"]) == 2
    first = data["links"][0]
    assert first["url"] == "https://jwc.mycc.edu.cn/info/1012/101.htm"
    assert first["date"] == "2026-10-01"


# ==================== 原页支持判定（requires_js） ====================

def test_requires_js_detects_spa_hosts():
    """超星系 SPA 站点：正文由脚本注入，原页渲染必然白屏 → 判定为需要 JS。"""
    assert requires_js("https://lib.mycc.edu.cn/")
    assert requires_js("https://lib.mycc.edu.cn/entry/page/x")
    # 子域通配（endswith("." + host) 分支）
    assert requires_js("https://passport2.chaoxing.com/login")


def test_requires_js_false_for_static_cms():
    """博达 CMS 静态页：原页渲染可用，不应被误判。"""
    assert not requires_js("https://jwc.mycc.edu.cn/jwgl/tzgg.htm")
    assert not requires_js("https://mksxy.mycc.edu.cn/")
    assert not requires_js("https://www.mycc.edu.cn/mcyx/")
    # 形近域名不得误命中（mycc 与 lib.mycc 是不同主机）
    assert not requires_js("https://notlib.mycc.edu.cn/")
    assert not requires_js("https://lib.mycc.edu.cn.evil.com/")


def test_requires_js_handles_bad_url():
    """非法地址不抛异常，按「不需要 JS」处理（由 is_allowed_url 另行拦截）。"""
    assert not requires_js("")
    assert not requires_js("not-a-url")

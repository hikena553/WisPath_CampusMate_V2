# 绵城印象 tab 重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将学生端「绵城印象」tab 重构为教务处官网风格布局，接入教务处/学院/图书馆实时爬取数据，并全局应用 3D 倾斜鼠标效果。

**Architecture:**
- 后端：新增 `campus_impression_items` 表统一存储爬取结果；新增解析器函数 + 爬虫服务 + 聚合 API；FastAPI lifespan 内启动 asyncio 后台定时任务，每 30 分钟"先入库再更新缓存"。
- 图书馆：使用 Playwright（已安装，Chromium 已就绪）渲染 SPA 后提取"新闻公告"标题+日期。
- 前端：重写 `CampusPage.vue` 的 `impression` tab 模板 + 全局 3D 倾斜指令。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, httpx, BeautifulSoup4, Playwright, Vue 3, TypeScript, Vitest

---

### Task 1: 数据模型 CampusImpressionItem + 迁移

**Files:**
- Create: `backend/app/models/campus.py`（追加类）
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/<rev>_add_campus_impression_items.py`

- [ ] **Step 1: 在 `backend/app/models/campus.py` 末尾追加模型**

```python
class CampusImpressionItem(Base):
    """教务处/学院/图书馆爬取结果统一存储"""
    __tablename__ = "campus_impression_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), index=True)      # jwc_entries/jwc_jxdt/jwc_tzgg/jwc_gjxx/jwc_jxjs/college_news/library
    college_key: Mapped[str | None] = mapped_column(String(50), index=True, default=None)
    title: Mapped[str] = mapped_column(String(200))
    image_url: Mapped[str | None] = mapped_column(String(500), default=None)
    url: Mapped[str] = mapped_column(String(500))
    date: Mapped[str | None] = mapped_column(String(20), default=None)
    fetched_at: Mapped[str] = mapped_column(String(30))
```

- [ ] **Step 2: 注册到 `backend/app/models/__init__.py`**

在 `from app.models.campus import CampusFigure, CampusScenery` 行改为：
```python
from app.models.campus import CampusFigure, CampusScenery, CampusImpressionItem
```

- [ ] **Step 3: 生成 alembic 迁移**

在 `backend/` 目录运行：
```bash
cd backend
alembic revision --autogenerate -m "add campus_impression_items"
```
（若 autogenerate 因索引/默认值差异报错，手动编写迁移，参考 `f2db7e9a2220` 的写法）

迁移内容（upgrade）：
```python
op.create_table('campus_impression_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('college_key', sa.String(length=50), nullable=True),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=True),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('date', sa.String(length=20), nullable=True),
    sa.Column('fetched_at', sa.String(length=30), nullable=False),
    sa.PrimaryKeyConstraint('id')
)
op.create_index(op.f('ix_campus_impression_items_source'), 'campus_impression_items', ['source'], unique=False)
op.create_index(op.f('ix_campus_impression_items_college_key'), 'campus_impression_items', ['college_key'], unique=False)
```

- [ ] **Step 4: 应用迁移**

```bash
cd backend
alembic upgrade head
```
Expected: 无报错，`campus_impression_items` 表创建成功。

- [ ] **Step 5: 运行现有测试确认无回归**

```bash
cd backend
pytest tests/test_tool_registry.py -q
```
Expected: 通过。

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/campus.py backend/app/models/__init__.py backend/alembic/versions/
git commit -m "feat: add campus_impression_items model and migration"
```

---

### Task 2: 解析器扩展（announcement_parser.py）

**Files:**
- Modify: `backend/app/utils/announcement_parser.py`
- Test: `backend/tests/test_announcement_parser.py`（新建）

在 `AnnouncementItem` dataclass 追加 `image_url` 字段，并新增各解析函数。

- [ ] **Step 1: 先写失败测试 `backend/tests/test_announcement_parser.py`**

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
cd backend
pytest tests/test_announcement_parser.py -q
```
Expected: 多个 `ImportError` / `AttributeError`。

- [ ] **Step 3: 实现解析器扩展**

在 `backend/app/utils/announcement_parser.py` 中修改 `AnnouncementItem` 并追加函数：

```python
import re
from dataclasses import dataclass, field


@dataclass
class AnnouncementItem:
    title: str
    date: str | None = None
    url: str | None = None
    image_url: str | None = None
    college_key: str | None = None
    source: str | None = None


def _absolute(base_url: str, href: str) -> str:
    href = href.replace("../", "/")
    if href.startswith("http"):
        return href
    return base_url.rstrip("/") + "/" + href.lstrip("/")


def parse_announcement_list(html: str, base_url: str = "https://jwc.mycc.edu.cn") -> list[AnnouncementItem]:
    """通知公告列表（兼容现有调用）"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.find_all("li"):
        a = li.find("a")
        if not a:
            continue
        href = a.get("href", "")
        if "info/1011/" not in href:
            continue
        text = a.get_text(strip=True)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})$", text)
        date = date_match.group(1) if date_match else None
        title = text[:-10] if date else text
        items.append(AnnouncementItem(title=title, date=date, url=_absolute(base_url, href)))
    return items


def parse_system_entries(html: str, base_url: str = "https://jwc.mycc.edu.cn") -> list[AnnouncementItem]:
    """教务处首页 .function-icons 系统入口"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select(".function-icons a.icon-item"):
        p = a.find("p")
        href = a.get("href", "")
        if not p or not href:
            continue
        items.append(AnnouncementItem(title=p.get_text(strip=True), url=_absolute(base_url, href)))
    return items


def parse_news_list(html: str, base_url: str = "https://jwc.mycc.edu.cn", url_marker: str | None = "info/") -> list[AnnouncementItem]:
    """通用新闻列表：教学动态/通知公告/高教信息/教学建设。

    url_marker 为 None 时不过滤 href（外链列表，如高教信息）。
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if url_marker and url_marker not in href:
            continue
        if not href.startswith("http") and "info/" not in href and url_marker:
            continue
        text = a.get_text(strip=True)
        if len(text) < 6 or text in ("查看更多", "更多", "查看详情"):
            continue
        # 去掉日期残留：支持 2024-11-15 / 2024.04.01 / 2026-07-31 / 2026.04.01
        date_match = re.search(r"(\d{4}[-.]\d{2}[-.]\d{2}|\d{4}-\d{2}|\d{2}-\d{2})", text)
        date = date_match.group(1) if date_match else None
        if date:
            text = text.replace(date, "").strip()
        # 去掉 "<span>31</span><p>2026-07</p>" 型分离日期（教学动态列表）
        if not date:
            sp = re.search(r"(\d{2})[^\d]?(\d{4})[-.](\d{2})", text)
            if sp:
                date = f"{sp.group(2)}-{sp.group(3)}-{sp.group(1)}"
                text = re.sub(r"\d{2}", "", text, count=1).strip()
        if not date:
            ym = re.search(r"(\d{4})-(\d{2})\b", text)
            if ym:
                date = f"{ym.group(1)}-{ym.group(2)}"
        items.append(AnnouncementItem(title=text, date=date, url=_absolute(base_url, href)))
    return items


def parse_detail_first_image(html: str, base_url: str = "https://jwc.mycc.edu.cn") -> str | None:
    """从新闻详情页正文提取第一张 __local 图片"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "__local" in src:
            return _absolute(base_url, src)
    return None


def parse_college_news(html: str, college_key: str, base_url: str) -> list[AnnouncementItem]:
    """学院首页新闻列表：取 href 含 /info/ 的 a 标签"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "info/" not in href:
            continue
        text = a.get_text(strip=True)
        if len(text) < 6 or text in ("查看更多", "更多", "进入官网", "查看详情"):
            continue
        date_match = re.search(r"(\d{4}[-.]\d{2}[-.]\d{2})", text)
        date = date_match.group(1) if date_match else None
        title = text.replace(date, "").strip() if date else text
        url = _absolute(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        items.append(AnnouncementItem(title=title, date=date, url=url, college_key=college_key))
    return items
```

- [ ] **Step 4: 运行确认通过**

```bash
cd backend
pytest tests/test_announcement_parser.py -q
```
Expected: PASS。若 `test_parses_jxdt_date_split` 日期组装失败，调整 Step 3 中的分离日期正则逻辑。

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/announcement_parser.py backend/tests/test_announcement_parser.py
git commit -m "feat: extend announcement parser for jxdt/gjxx/jxjs/college/library pages"
```

---

### Task 3: 爬虫服务 impression_crawler.py

**Files:**
- Create: `backend/app/services/impression_crawler.py`
- Modify: `backend/requirements.txt`（追加 playwright）
- Test: `backend/tests/test_impression_crawler.py`（新建）

- [ ] **Step 1: 追加 playwright 到 requirements.txt**

在文件末尾追加：
```
playwright>=1.40.0
```

- [ ] **Step 2: 写失败测试 `backend/tests/test_impression_crawler.py`**

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.impression_crawler import (
    fetch_jwc_entries,
    fetch_jwc_jxdt,
    fetch_college_news,
    fetch_library_news,
    crawl_all,
    refresh_impression_data,
)


class TestJwcCrawlers:
    def test_fetch_jwc_entries_sync(self):
        with patch("httpx.get") as mock_get:
            resp = MagicMock()
            resp.text = '<div class="function-icons"><a class="icon-item" href="/x.htm"><p>教务管理系统</p></a></div>'
            mock_get.return_value = resp
            items = fetch_jwc_entries()
            assert items[0].title == "教务管理系统"

    def test_fetch_jwc_jxdt_fetches_images(self):
        list_html = '<ul><li><a href="info/1012/1.htm"><h3>测试动态</h3></a></li></ul>'
        detail_html = '<div><img src="/__local/ABC/IMG.png"></div>'
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(text=list_html),
                MagicMock(text=detail_html),
            ]
            items = fetch_jwc_jxdt()
            assert items[0].image_url.endswith("IMG.png")

    def test_fetch_jwc_jxdt_drops_no_image(self):
        list_html = '<ul><li><a href="info/1012/2.htm"><h3>无图动态</h3></a></li></ul>'
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(text=list_html),
                MagicMock(text="<div>no image</div>"),
            ]
            items = fetch_jwc_jxdt()
            assert items == []


class TestCollegeCrawler:
    def test_fetch_college_news_loops_sites(self):
        html = '<a href="info/1/2.htm">学院新闻标题 <span>2026.07.15</span></a>'
        with patch("httpx.get") as mock_get:
            mock_get.return_value = MagicMock(text=html)
            items = fetch_college_news()
            assert len(items) >= 7
            assert items[0].source == "college_news"
            assert items[0].college_key


class TestLibraryCrawler:
    def test_fetch_library_news(self):
        with patch("app.services.impression_crawler._library_news_via_playwright") as mock_pw:
            mock_pw.return_value = [
                AnnouncementItem(title="图书馆2026年暑期开放安排通知", date="2026-07-10", url="https://lib.mycc.edu.cn/"),
            ]
            items = fetch_library_news()
            assert items[0].title == "图书馆2026年暑期开放安排通知"
            assert items[0].source == "library"


class TestRefresh:
    def test_refresh_impression_data_inserts_then_caches(self):
        with patch("app.services.impression_crawler.crawl_all") as mock_crawl, \
             patch("app.services.impression_crawler._save_to_db") as mock_save, \
             patch("app.services.impression_crawler._set_impression_cache") as mock_cache:
            mock_crawl.return_value = [AnnouncementItem(title="t", url="u")]
            refresh_impression_data()
            mock_save.assert_called_once()
            mock_cache.assert_called_once()
```

注意：测试文件顶部需导入 `AnnouncementItem`：
```python
from app.utils.announcement_parser import AnnouncementItem
```

- [ ] **Step 3: 运行确认失败**

```bash
cd backend
pytest tests/test_impression_crawler.py -q
```
Expected: `ModuleNotFoundError: No module named 'app.services.impression_crawler'`

- [ ] **Step 4: 实现 `backend/app/services/impression_crawler.py`**

```python
"""绵城印象爬虫服务：抓取 → 入库 → 更新缓存"""
import asyncio
import logging
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.campus import CampusImpressionItem
from app.utils.announcement_parser import (
    AnnouncementItem,
    parse_system_entries,
    parse_news_list,
    parse_detail_first_image,
    parse_college_news,
)

logger = logging.getLogger(__name__)

JWC_BASE = "https://jwc.mycc.edu.cn"

JWC_PAGES = {
    "jwc_jxdt": ("/jwgl/jxdt.htm", "info/1012/"),
    "jwc_tzgg": ("/jwgl/tzgg.htm", "info/1011/"),
    "jwc_gjxx": ("/gjxx.htm", None),
    "jwc_jxjs": ("/jxjs.htm", "info/"),
}

COLLEGES = {
    "马克思主义学院": "https://mksxy.mycc.edu.cn/",
    "人工智能学院": "https://xdjsxy.mycc.edu.cn/",
    "智能制造与工程学院": "https://xdcsjsxy.mycc.edu.cn/",
    "健康与教育学院": "https://xdfw.mycc.edu.cn/",
    "商学院": "https://jgxy.mycc.edu.cn/",
    "创意设计学院": "https://cysjxy.mycc.edu.cn/",
    "终身教育学院": "https://jxjy.mycc.edu.cn/",
}

_impression_cache: dict[str, Any] | None = None
_impression_cache_ts = 0.0
IMPRESSION_TTL = 300


def _set_impression_cache(data: list[dict]) -> None:
    global _impression_cache, _impression_cache_ts
    _impression_cache = data
    _impression_cache_ts = time.time()


def get_impression_cache() -> list[dict] | None:
    if _impression_cache is not None and time.time() - _impression_cache_ts < IMPRESSION_TTL:
        return _impression_cache
    return None


def _get(url: str, timeout: float = 10) -> str:
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.encoding = resp.encoding or "utf-8"
    return resp.text


def fetch_jwc_entries() -> list[AnnouncementItem]:
    html = _get(JWC_BASE + "/")
    items = parse_system_entries(html, base_url=JWC_BASE)
    for it in items:
        it.source = "jwc_entries"
    return items


def fetch_jwc_jxdt() -> list[AnnouncementItem]:
    """教学动态：列表 + 详情页取首图，无图丢弃"""
    path, marker = JWC_PAGES["jwc_jxdt"]
    html = _get(JWC_BASE + path)
    items = parse_news_list(html, base_url=JWC_BASE, url_marker=marker)
    result = []
    for it in items[:10]:
        try:
            detail = _get(it.url)
        except Exception:
            continue
        img = parse_detail_first_image(detail, base_url=JWC_BASE)
        if not img:
            continue
        it.image_url = img
        it.source = "jwc_jxdt"
        result.append(it)
    return result


def fetch_jwc_simple(source: str) -> list[AnnouncementItem]:
    """通知公告/高教信息/教学建设"""
    path, marker = JWC_PAGES[source]
    html = _get(JWC_BASE + path)
    items = parse_news_list(html, base_url=JWC_BASE, url_marker=marker)
    for it in items:
        it.source = source
    return items[:10]


def fetch_college_news() -> list[AnnouncementItem]:
    items = []
    for name, url in COLLEGES.items():
        try:
            html = _get(url)
        except Exception as e:
            logger.warning("college %s fetch failed: %s", name, e)
            continue
        parsed = parse_college_news(html, college_key=name, base_url=url)
        for it in parsed[:2]:
            it.source = "college_news"
        items.extend(parsed[:2])
    return items


def _library_news_via_playwright() -> list[AnnouncementItem]:
    """用 Playwright 渲染图书馆 SPA，提取新闻公告标题+日期"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed")
        return []
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://lib.mycc.edu.cn/", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        text = page.inner_text("body")
        browser.close()
    # 新闻公告区块：从"新闻公告"标题后抓取 通知标题 + 日期
    idx = text.find("新闻公告")
    if idx == -1:
        return []
    chunk = text[idx: idx + 1200]
    lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
    titles: list[tuple[str, str]] = []
    for i, line in enumerate(lines):
        date_match = __import__("re").match(r"\d{4}-\d{2}-\d{2}", line)
        if date_match and i > 0:
            titles.append((lines[i - 1], line))
    for title, date in titles[:10]:
        items.append(AnnouncementItem(title=title, date=date, url="https://lib.mycc.edu.cn/", source="library"))
    return items


def fetch_library_news() -> list[AnnouncementItem]:
    return _library_news_via_playwright()


def crawl_all() -> list[AnnouncementItem]:
    """全量爬取：入口 + 教学动态 + 通知/高教/建设 + 学院 + 图书馆"""
    results: list[AnnouncementItem] = []
    results += fetch_jwc_entries()
    results += fetch_jwc_jxdt()
    for source in ("jwc_tzgg", "jwc_gjxx", "jwc_jxjs"):
        results += fetch_jwc_simple(source)
    results += fetch_college_news()
    results += fetch_library_news()
    return results


def _save_to_db(items: list[AnnouncementItem]) -> None:
    db: Session = SessionLocal()
    try:
        db.query(CampusImpressionItem).delete()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for it in items:
            db.add(CampusImpressionItem(
                source=it.source,
                college_key=it.college_key,
                title=it.title,
                image_url=it.image_url,
                url=it.url or "",
                date=it.date,
                fetched_at=now,
            ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("save impression failed: %s", e)
    finally:
        db.close()


def refresh_impression_data() -> list[dict]:
    """定时任务入口：先入库再更新缓存"""
    try:
        items = crawl_all()
        _save_to_db(items)
        data = [vars(i) for i in items]
        _set_impression_cache(data)
        return data
    except Exception:
        logger.exception("refresh impression failed")
        return get_impression_cache() or []
```

- [ ] **Step 5: 运行确认通过**

```bash
cd backend
pytest tests/test_impression_crawler.py -q
```
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/impression_crawler.py backend/tests/test_impression_crawler.py backend/requirements.txt
git commit -m "feat: add impression crawler service"
```

---

### Task 4: 聚合 API + 后台定时任务

**Files:**
- Modify: `backend/app/api/campus.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 `backend/app/api/campus.py` 追加聚合接口**

在文件末尾追加：

```python
from app.services.impression_crawler import get_impression_cache, refresh_impression_data


@router.get("/impression")
def get_impression(db: Session = Depends(get_db)):
    """绵城印象聚合数据：缓存 → 数据库 → 实时爬取兜底"""
    cached = get_impression_cache()
    if cached is not None:
        return cached
    rows = db.query(CampusImpressionItem).order_by(CampusImpressionItem.id.desc()).limit(500).all()
    if rows:
        data = [
            {"source": r.source, "college_key": r.college_key, "title": r.title,
             "image_url": r.image_url, "url": r.url, "date": r.date, "fetched_at": r.fetched_at}
            for r in rows
        ]
        return data
    # 数据库为空 → 实时爬取兜底
    return refresh_impression_data()
```

同时将文件顶部的 `from app.models.campus import CampusFigure, CampusScenery` 改为：
```python
from app.models.campus import CampusFigure, CampusScenery, CampusImpressionItem
```

- [ ] **Step 2: 在 `backend/app/main.py` lifespan 启动后台定时任务**

修改 `main.py`：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import importlib
    importlib.import_module("app.seed")
    from app.services.impression_crawler import refresh_impression_data
    task = asyncio.create_task(_periodic_refresh())
    yield
    task.cancel()


async def _periodic_refresh():
    import asyncio
    from app.services.impression_crawler import refresh_impression_data
    while True:
        try:
            refresh_impression_data()  # 阻塞抓取在后台线程安全吗？见备注
        except Exception:
            pass
        await asyncio.sleep(1800)  # 30 分钟
```

> 注意：`refresh_impression_data` 是同步阻塞函数，在 asyncio 事件循环中直接调用会阻塞。正确做法是用 `asyncio.to_thread` 包装：

```python
async def _periodic_refresh():
    import asyncio
    from app.services.impression_crawler import refresh_impression_data
    while True:
        try:
            await asyncio.to_thread(refresh_impression_data)
        except Exception:
            pass
        await asyncio.sleep(1800)
```

- [ ] **Step 3: 启动后端验证接口**

```bash
cd backend
uvicorn app.main:app --port 8000
```
然后访问 `http://localhost:8000/api/campus/impression`。
Expected: 返回 JSON 数组（含 jwc_entries/jwc_jxdt/college_news/library 等 source）。首次访问会触发实时爬取，约 10-30 秒。

- [ ] **Step 4: 清理临时校验文件（docs/superpowers 外的探针脚本位于 TEMP，无需清理）**

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/campus.py backend/app/main.py
git commit -m "feat: add campus/impression API and 30min background refresh"
```

---

### Task 5: 前端类型与 API 函数

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/campus.ts`

- [ ] **Step 1: 在 `frontend/src/types/index.ts` 追加类型**

```ts
export interface ImpressionItem {
  source: string
  college_key: string | null
  title: string
  image_url: string | null
  url: string
  date: string | null
  fetched_at: string | null
}
```

- [ ] **Step 2: 在 `frontend/src/api/campus.ts` 追加函数**

```ts
import type { CampusFigure, CampusScenery, Announcement, ImpressionItem } from '@/types'

export function getImpression() {
  return request.get<ImpressionItem[]>('/campus/impression')
}
```

- [ ] **Step 3: TypeScript 检查**

```bash
cd frontend
npx vue-tsc --noEmit
```
Expected: 无新增错误（可能有存量错误，仅确认不新增）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/campus.ts
git commit -m "feat: add frontend impression types and API"
```

---

### Task 6: 前端 CampusPage.vue 重构 + 3D 倾斜

**Files:**
- Modify: `frontend/src/views/student/CampusPage.vue`

- [ ] **Step 1: 重写 `impression` tab 模板**

替换 `CampusPage.vue` 中 `<template v-else-if="activeTab === 'impression'">` 整个区块（第 57-94 行），新模板包含 6 个区块：教务系统入口 / 教学动态+通知公告 / 高教信息+教学建设 / 专业分院(实时新闻) / 图书馆公告 / 绵城印象。

模板核心结构（完整代码）：
```html
<template v-else-if="activeTab === 'impression'">
  <!-- ① 教务系统入口 -->
  <div class="imp-section">
    <div class="imp-sec-title"><span class="sec-dot"></span> 教务系统入口</div>
    <div class="entry-grid">
      <div v-for="e in impression.entries" :key="e.url" class="entry-item" @click="openLink(e.url)">
        <span class="entry-icon">{{ entryIcon(e.title) }}</span>
        <p>{{ e.title }}</p>
      </div>
    </div>
  </div>

  <!-- ② 教学动态 + 通知公告 -->
  <div class="imp-duo">
    <div class="imp-card">
      <div class="imp-card-head">
        <span class="imp-card-title">📰 教学动态</span>
        <a class="imp-more" href="https://jwc.mycc.edu.cn/jwgl/jxdt.htm" target="_blank">查看详情 →</a>
      </div>
      <div v-if="impression.jxdt.length" class="jxdt-first" @click="openLink(impression.jxdt[0].url)">
        <img :src="impression.jxdt[0].image_url" class="jxdt-first-img" />
        <span class="jxdt-first-title">{{ impression.jxdt[0].title }}</span>
      </div>
      <div v-for="a in impression.jxdt.slice(1)" :key="a.url" class="news-row" @click="openLink(a.url)">
        <span class="news-date">{{ shortDate(a.date) }}</span>
        <span class="news-text">{{ a.title }}</span>
      </div>
    </div>
    <div class="imp-card">
      <div class="imp-card-head">
        <span class="imp-card-title">📢 通知公告</span>
        <a class="imp-more" href="https://jwc.mycc.edu.cn/jwgl/tzgg.htm" target="_blank">查看详情 →</a>
      </div>
      <div v-for="a in impression.tzgg" :key="a.url" class="announce-row" @click="openLink(a.url)">
        <span class="announce-date">{{ a.date }}</span>
        <span class="news-text">{{ a.title }}</span>
      </div>
    </div>
  </div>

  <!-- ③ 高教信息 + 教学建设 -->
  <div class="imp-duo">
    <div class="imp-card">
      <div class="imp-card-head">
        <span class="imp-card-title">🎓 高教信息</span>
        <a class="imp-more" href="https://jwc.mycc.edu.cn/gjxx.htm" target="_blank">查看详情 →</a>
      </div>
      <div v-for="a in impression.gjxx" :key="a.url" class="news-row" @click="openLink(a.url)">
        <span class="news-date">{{ a.date }}</span>
        <span class="news-text">{{ a.title }}</span>
      </div>
    </div>
    <div class="imp-card">
      <div class="imp-card-head">
        <span class="imp-card-title">📚 教学建设</span>
        <a class="imp-more" href="https://jwc.mycc.edu.cn/jxjs.htm" target="_blank">查看详情 →</a>
      </div>
      <div v-for="a in impression.jxjs" :key="a.url" class="news-row" @click="openLink(a.url)">
        <span class="news-date">{{ a.date }}</span>
        <span class="news-text">{{ a.title }}</span>
      </div>
    </div>
  </div>

  <!-- ④ 专业分院（实时新闻） -->
  <div class="imp-section">
    <div class="imp-sec-title"><span class="sec-dot"></span> 专业分院
      <span class="imp-tag">新闻实时更新</span>
    </div>
    <div class="college-grid">
      <div v-for="(c, ci) in collegeCards" :key="c.name" class="college-card" @click="openLink(c.url)">
        <div class="college-head">
          <span class="college-icon">{{ c.icon }}</span>
          <span class="college-name">{{ c.name }}</span>
        </div>
        <div v-for="n in impression.collegeNews[c.name] || []" :key="n.url" class="college-news">
          <span class="news-dot">▪</span><span class="news-text">{{ n.title }}</span>
        </div>
        <span class="college-link">进入官网 →</span>
      </div>
    </div>
  </div>

  <!-- ⑤ 图书馆公告 -->
  <div class="imp-card imp-library">
    <div class="imp-card-head">
      <span class="imp-card-title">📚 图书馆公告</span>
      <div class="imp-head-right">
        <span class="imp-tag">30分钟更新</span>
        <a class="imp-more" href="https://lib.mycc.edu.cn/" target="_blank">进入图书馆官网 →</a>
      </div>
    </div>
    <div v-for="a in impression.library" :key="a.title" class="news-row" @click="openLink(a.url)">
      <span class="news-date">{{ a.date }}</span>
      <span class="news-text">{{ a.title }}</span>
    </div>
  </div>

  <!-- ⑥ 绵城印象 -->
  <div class="imp-section">
    <div class="imp-sec-title"><span class="sec-dot"></span> 绵城印象</div>
    <div class="imp-grid">
      <div v-for="item in impressionItems" :key="item.title" class="imp-card-link" @click="openLink(item.url)">
        <span class="link-icon">{{ item.icon }}</span>
        <div class="link-text">
          <strong>{{ item.title }}</strong>
          <small>了解更多 →</small>
        </div>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: 更新 `<script setup>` 部分**

替换 `impressionItems`/`collegeItems` 相关代码，新增：

```ts
import { getImpression, type ImpressionItem } from '@/api/campus'

const impressionData = ref<ImpressionItem[]>([])

const impression = computed(() => {
  const all = impressionData.value
  const bySource = (s: string) => all.filter(i => i.source === s)
  return {
    entries: bySource('jwc_entries'),
    jxdt: bySource('jwc_jxdt'),
    tzgg: bySource('jwc_tzgg'),
    gjxx: bySource('jwc_gjxx'),
    jxjs: bySource('jwc_jxjs'),
    library: bySource('library'),
    collegeNews: groupCollegeNews(all),
  }
})

function groupCollegeNews(all: ImpressionItem[]): Record<string, ImpressionItem[]> {
  const map: Record<string, ImpressionItem[]> = {}
  for (const i of all.filter(x => x.source === 'college_news')) {
    if (!map[i.college_key!]) map[i.college_key!] = []
    map[i.college_key!].push(i)
  }
  return map
}

const collegeCards = [
  { name: '马克思主义学院', url: 'https://mksxy.mycc.edu.cn/', icon: '📖' },
  { name: '人工智能学院', url: 'https://xdjsxy.mycc.edu.cn/', icon: '🤖' },
  { name: '智能制造与工程学院', url: 'https://xdcsjsxy.mycc.edu.cn/', icon: '⚙️' },
  { name: '健康与教育学院', url: 'https://xdfw.mycc.edu.cn/', icon: '🏥' },
  { name: '商学院', url: 'https://jgxy.mycc.edu.cn/', icon: '📊' },
  { name: '创意设计学院', url: 'https://cysjxy.mycc.edu.cn/', icon: '🎨' },
  { name: '终身教育学院', url: 'https://jxjy.mycc.edu.cn/', icon: '📚' },
]

function entryIcon(title: string) {
  const map: Record<string, string> = {
    '教务管理系统': '🖥️', '实习管理系统': '🏢', '实验管理平台': '🧪',
    '超星在线学习平台': '📖', '教学质量管理平台': '📊', '毕业论文(设计)管理系统': '📝',
    '教学校历': '🗓️', '作息时间': '⏰', '课表查询': '📋',
  }
  return map[title] || '🔗'
}

function shortDate(d: string | null) {
  if (!d) return ''
  const m = d.match(/\d{4}[-.]\d{2}[-.]\d{2}/)
  return m ? m[0].replace(/\./g, '-') : d
}

async function loadImpression() {
  try {
    impressionData.value = await getImpression()
  } catch { /* 静默 */ }
}
```

在 `onMounted` 中追加 `loadImpression()`，并删除 `campusLifeItems` 数组。

- [ ] **Step 3: 新增样式 + 全局 3D 倾斜**

在 `<style scoped>` 追加：

```css
/* ===== Impression ===== */
.imp-section { margin-bottom: 24px; }
.imp-sec-title { font-size: 16px; font-weight: 600; color: #1a1a2e; display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.imp-tag { font-size: 11px; color: #999; background: #f5f7fa; padding: 2px 10px; border-radius: 10px; font-weight: 400; }
.entry-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 12px; }
.entry-item { background: #f5f7fa; border-radius: 10px; padding: 14px 6px; text-align: center; cursor: pointer; transition: transform .18s ease, box-shadow .18s ease; }
.entry-icon { font-size: 26px; display: block; }
.entry-item p { font-size: 12px; color: #444; margin: 6px 0 0; }
.imp-duo { display: flex; gap: 18px; margin-bottom: 22px; }
.imp-card { flex: 1; background: #fff; border-radius: 14px; padding: 16px 18px; box-shadow: 0 1px 6px rgba(0,0,0,.04); transition: transform .18s ease, box-shadow .18s ease; }
.imp-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.imp-card-title { font-size: 15px; font-weight: 700; color: #1a1a2e; border-left: 3px solid #409eff; padding-left: 8px; }
.imp-more { font-size: 12px; color: #409eff; text-decoration: none; }
.imp-head-right { display: flex; gap: 12px; align-items: center; }
.jxdt-first { position: relative; border-radius: 8px; overflow: hidden; margin-bottom: 12px; cursor: pointer; }
.jxdt-first-img { width: 100%; height: 120px; object-fit: cover; display: block; }
.jxdt-first-title { position: absolute; left: 0; right: 0; bottom: 0; padding: 24px 12px 10px; background: linear-gradient(transparent, rgba(0,0,0,.65)); color: #fff; font-size: 13px; font-weight: 600; }
.news-row { display: flex; align-items: center; gap: 10px; font-size: 13px; color: #444; line-height: 2.05; cursor: pointer; }
.news-row:hover .news-text { color: #409eff; }
.news-date { color: #999; font-size: 12px; flex-shrink: 0; width: 86px; }
.news-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.announce-row { display: flex; align-items: center; gap: 10px; font-size: 13px; color: #444; line-height: 2.05; cursor: pointer; }
.announce-date { color: #409eff; font-size: 12px; flex-shrink: 0; width: 56px; font-weight: 600; }
.announce-row:hover .news-text { color: #409eff; }
.college-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
.college-card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 6px rgba(0,0,0,.04); cursor: pointer; transition: transform .18s ease, box-shadow .18s ease; }
.college-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.college-icon { font-size: 28px; }
.college-name { font-size: 15px; font-weight: 700; color: #1a1a2e; }
.college-news { display: flex; gap: 6px; font-size: 12px; color: #666; line-height: 1.85; }
.news-dot { color: #409eff; flex-shrink: 0; }
.college-link { margin-top: 10px; display: inline-block; font-size: 12px; color: #409eff; }
.imp-library { margin-bottom: 22px; }
.imp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.imp-card-link { display: flex; align-items: center; gap: 14px; padding: 16px 18px; background: #fff; border-radius: 12px; cursor: pointer; border: 1px solid rgba(0,0,0,.04); box-shadow: 0 1px 6px rgba(0,0,0,.02); transition: transform .18s ease, box-shadow .18s ease; }

/* 3D 倾斜统一处理：卡片元素 */
.entry-item, .imp-card, .college-card, .imp-card-link { transform-style: preserve-3d; }

/* 移动端 */
@media (max-width: 767px) {
  .imp-duo { flex-direction: column; }
  .entry-grid { grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); }
  .college-grid { grid-template-columns: repeat(2, 1fr); }
  .imp-grid { grid-template-columns: repeat(2, 1fr); }
}
```

- [ ] **Step 4: 新增 3D 倾斜指令**

创建 `frontend/src/directives/tilt.ts`：

```ts
import type { Directive } from 'vue'

export const tilt: Directive<HTMLElement> = {
  mounted(el) {
    el.style.transformStyle = 'preserve-3d'
    el.style.transition = 'transform .18s ease, box-shadow .18s ease'
    el.addEventListener('mousemove', (e: MouseEvent) => {
      const r = el.getBoundingClientRect()
      const x = (e.clientX - r.left) / r.width - 0.5
      const y = (e.clientY - r.top) / r.height - 0.5
      el.style.transform = `rotateY(${x * 6}deg) rotateX(${-y * 6}deg)`
      el.style.boxShadow = `0 ${6 + Math.abs(y * 8)}px 14px rgba(0,0,0,.10)`
    })
    el.addEventListener('mouseleave', () => {
      el.style.transform = ''
      el.style.boxShadow = ''
    })
  },
}
```

在 `CampusPage.vue` 中应用：

```ts
import { tilt } from '@/directives/tilt'
// <script setup> 中注册指令
const vTilt = tilt
```

模板中给卡片元素加 `v-tilt`：
```html
<div class="entry-item" v-tilt ...>
<div class="imp-card" v-tilt ...>
<div class="college-card" v-tilt ...>
<div class="imp-card-link" v-tilt ...>
```

- [ ] **Step 5: 构建验证**

```bash
cd frontend
npm run build
```
Expected: 构建成功（vue-tsc + vite）。若存量 TS 错误阻塞，运行 `npx vue-tsc --noEmit` 排查新引入错误。

- [ ] **Step 6: 运行前端测试**

```bash
cd frontend
npm test
```
Expected: 现有测试通过。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/student/CampusPage.vue frontend/src/directives/tilt.ts
git commit -m "feat: redesign impression tab with real-time campus data and 3D tilt"
```

---

### Task 7: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd backend
uvicorn app.main:app --port 8000
```

- [ ] **Step 2: 启动前端**

```bash
cd frontend
npm run dev
```

- [ ] **Step 3: 浏览器验证**

登录学生账号（`2024001` / `123456`），进入"校园" →"绵城印象" tab，确认：
- [ ] 6 个区块顺序正确（入口→动态/公告→高教/建设→专业分院→图书馆→绵城印象）
- [ ] 教学动态带真实图片（详情页首图）
- [ ] 通知公告/高教信息/教学建设显示真实标题+日期
- [ ] 专业分院 7 个学院卡片各显示实时新闻
- [ ] 图书馆公告显示真实通知（Playwright 渲染）
- [ ] 所有卡片 3D 倾斜生效
- [ ] 点击卡片跳转对应官网

- [ ] **Step 4: 定时任务验证**

等待 30 分钟后刷新页面，或手动调用 `/api/campus/impression` 观察 `fetched_at` 更新。

- [ ] **Step 5: 运行后端全量测试**

```bash
cd backend
pytest -q
```
Expected: 全部通过。

- [ ] **Step 6: 最终提交**

```bash
git add -A
git commit -m "chore: verify impression feature end-to-end"
```

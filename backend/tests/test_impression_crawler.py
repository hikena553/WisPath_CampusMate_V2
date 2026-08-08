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
from app.utils.announcement_parser import AnnouncementItem


class TestJwcCrawlers:
    def test_fetch_jwc_entries_sync(self):
        with patch("httpx.get") as mock_get:
            resp = MagicMock()
            resp.text = '<div class="function-icons"><a class="icon-item" href="/x.htm"><p>教务管理系统</p></a></div>'
            mock_get.return_value = resp
            items = fetch_jwc_entries()
            assert items[0].title == "教务管理系统"

    def test_fetch_jwc_jxdt_fetches_images(self):
        list_html = '<ul><li><a href="info/1012/1.htm"><h3>测试教学动态新闻标题</h3></a></li></ul>'
        detail_html = '<div><img src="/__local/ABC/IMG.png"></div>'
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(text=list_html),
                MagicMock(text=detail_html),
            ]
            items = fetch_jwc_jxdt()
            assert items[0].image_url.endswith("IMG.png")

    def test_fetch_jwc_jxdt_drops_no_image(self):
        list_html = '<ul><li><a href="info/1012/2.htm"><h3>无图动态测试新闻标题</h3></a></li></ul>'
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

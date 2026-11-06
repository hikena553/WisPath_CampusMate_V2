"""资讯账号转发管道：频率节流、跨源标题重复、arXiv feed_key 对齐。

对应四个实测问题（2026-11-06 库内数据）：
1. 一个账号在同一秒连发 20 条 → 与「逐条转发频率（最小间隔）」配置语义相反；
2. 同一条新闻被两个源收录时发两帖（Gemini Omni 1.2 出现两次）；
3. 每日汇总里同样重复收录同一标题；
4. arXiv 条目 feed_key 写死 "arxiv"，与资讯源 export_arxiv_org_1 不一致，
   连接线过滤把它们全挡掉 —— 论文速递账号自 11-05 起静默停更。
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func

from app.models.community import CommunityPost
from app.models.feed import ExternalFeedItem, FeedSource
from app.models.media import MediaAccount, MediaPost, MediaSourceLink
from app.models.user import UserRole
from app.services import feed_ingest
from app.services import media_account_service as mas


@pytest.fixture(autouse=True)
def _clean_feed_items(db):
    """每个用例前后清掉本轮新入库的资讯条目。

    否则前一个用例造的条目会在后一个用例里成为「尚未转发的候选」，
    relay 逻辑据此再发一条，去重断言就会误判。
    """
    max_id = db.query(func.max(ExternalFeedItem.id)).scalar() or 0
    yield
    db.query(ExternalFeedItem).filter(ExternalFeedItem.id > max_id).delete(synchronize_session=False)
    db.commit()


def _link() -> str:
    return f"https://example.com/{uuid.uuid4().hex}"


def _item(db, *, title: str, source_type: str = "ai_news", feed_key: str = "test_key",
          summary: str | None = None, minutes_ago: int = 0,
          link: str | None = None) -> ExternalFeedItem:
    row = ExternalFeedItem(
        source_type=source_type,
        feed_key=feed_key,
        title=title,
        summary=summary,
        link=link or _link(),
        source_name="测试源",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture()
def media_account(db, make_user):
    """一个启用且已接入资讯站的账号（内容方向 ai_news，频率 30 分钟）。

    配一条专属连接线（feed_key=test_key）：否则该账号没有连接线时回落到「按分类」，
    会把种子里的真实 ai_news 条目也算成候选，断言就数不清是谁发的。
    """
    user = make_user(role=UserRole.MEDIA, name="测试资讯号")
    acc = MediaAccount(
        user_id=user.id,
        is_enabled=True,
        station_connected=True,
        content_scope=["ai_news"],
        relay_interval_minutes=30,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)

    source = FeedSource(
        name="转发测试源", kind="rss", source_type="ai_news",
        url=f"https://example.com/{uuid.uuid4().hex}", feed_key="test_key",
        per_page=10, enabled=True, is_builtin=False,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    db.add(MediaSourceLink(account_id=acc.id, feed_source_id=source.id, name="测试连接", enabled=True))
    db.commit()

    yield acc, user

    post_ids = [
        pid for (pid,) in db.query(MediaPost.post_id).filter(MediaPost.account_user_id == user.id).all()
    ]
    if post_ids:
        db.query(CommunityPost).filter(CommunityPost.id.in_(post_ids)).delete(synchronize_session=False)
    db.query(MediaPost).filter(MediaPost.account_user_id == user.id).delete()
    db.query(MediaSourceLink).filter(MediaSourceLink.account_id == acc.id).delete()
    db.query(MediaAccount).filter(MediaAccount.id == acc.id).delete()
    db.query(FeedSource).filter(FeedSource.id == source.id).delete()
    db.commit()


def _my_posts(db, user_id: int) -> int:
    """只数「本用例造的账号」发了多少 —— 种子里的 7 个真实资讯账号也在跑同一管道。"""
    return db.query(MediaPost).filter(MediaPost.account_user_id == user_id).count()


def _backdate_relay(db, user_id: int, minutes: int) -> None:
    """把该账号最近一条转发的发帖时间往前挪，绕开「最小间隔」节流，单测去重逻辑。"""
    post = (
        db.query(MediaPost)
        .filter(MediaPost.account_user_id == user_id, MediaPost.kind == "relay")
        .order_by(MediaPost.id.desc())
        .first()
    )
    assert post is not None
    post.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    cp = db.query(CommunityPost).filter(CommunityPost.id == post.post_id).first()
    if cp:
        cp.created_at = post.created_at
    db.commit()


def test_relay_posts_at_most_one_per_cycle(db, media_account):
    """频率节流：一轮只发一条。历史实现最多 20 条，同一秒刷满时间线。"""
    for i in range(3):
        _item(db, title=f"新资讯标题 {i}")

    mas.relay_new_items(db, window_minutes=40)

    assert _my_posts(db, media_account[1].id) == 1


def test_relay_skips_same_title_across_sources(db, media_account):
    """同一条新闻被两个源收录（标题一致、链接不同）时只发一次。"""
    title = "Gemini Omni 1.2 Flash: Fast and cost-effective with longer clips"
    _item(db, title=title)

    mas.relay_new_items(db, window_minutes=40)
    assert _my_posts(db, media_account[1].id) == 1
    _backdate_relay(db, media_account[1].id, minutes=120)

    # 另一个源收录的同一条新闻（标题一致、标点/大小写略有差异）
    _item(db, title="Gemini Omni 1.2 Flash：fast and cost-effective with longer clips")

    mas.relay_new_items(db, window_minutes=40)

    # 同一标题（仅标点/大小写不同）不再发第二条
    assert _my_posts(db, media_account[1].id) == 1


def test_relay_respects_min_interval(db, media_account):
    """最小间隔未到：即使有新条目也不再发。"""
    _item(db, title="第一条")
    mas.relay_new_items(db, window_minutes=40)
    assert _my_posts(db, media_account[1].id) == 1

    _item(db, title="第二条")
    mas.relay_new_items(db, window_minutes=40)

    assert _my_posts(db, media_account[1].id) == 1


def test_digest_items_dedupe_by_title(db, media_account):
    """每日汇总按标题去重：同一新闻两个源只收一次。"""
    acc, _ = media_account
    _item(db, title="Gemini Omni 1.2 Flash: Fast and cost-effective with longer clips")
    _item(db, title="Gemini Omni 1.2 Flash: Fast and cost-effective with longer clips")
    _item(db, title="另一条独立新闻")

    items = mas._pick_digest_items(db, acc.content_scope, {"test_key"})
    titles = [mas._norm_title(it.title) for it in items]

    assert len(titles) == len(set(titles))
    assert len(items) >= 2


def test_arxiv_items_use_source_feed_key(db, monkeypatch):
    """arXiv 抓取必须落到资讯源的 feed_key，否则连接线永远过滤不到。"""
    source = FeedSource(
        name="测试 arXiv", kind="arxiv", source_type="papers",
        url=f"https://export.arxiv.org/{uuid.uuid4().hex}", feed_key="export_arxiv_org_9",
        per_page=5, enabled=True, is_builtin=False,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    def fake_fetch(max_results=20, search_query=None):
        return [{
            "source_type": "papers", "feed_key": "arxiv", "title": "Fake Paper",
            "summary": "s", "link": _link(), "author": None, "source_name": "arXiv AI",
            "meta": {}, "published_at": None,
        }]

    monkeypatch.setattr(feed_ingest, "fetch_arxiv", fake_fetch)

    items = feed_ingest._fetch_one(db, source)

    assert items and items[0]["feed_key"] == "export_arxiv_org_9"
    assert items[0]["source_name"] == "测试 arXiv"

    db.query(ExternalFeedItem).filter(ExternalFeedItem.feed_key == "export_arxiv_org_9").delete()
    db.query(FeedSource).filter(FeedSource.id == source.id).delete()
    db.commit()


def test_backfill_legacy_feed_key(db):
    """历史条目 feed_key 回填：'lmarena' → 某个真实资讯源的 key，连接线才认。

    断言语义而不是某个具体值：全量跑时其它用例可能已经让种子里的 LMArena 源
    生成过 feed_key，回填先命中它也是正确行为 —— 关键是旧值必须被换成
    「库里真实存在的源 key」，否则连接线永远匹配不到。
    """
    source = FeedSource(
        name="回填用 LMArena", kind="lmarena", source_type="rankings",
        url=f"https://lmarena.ai/{uuid.uuid4().hex}", feed_key="lmarena_test_7",
        per_page=5, enabled=True, is_builtin=False,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    valid_keys = {
        k for (k,) in db.query(FeedSource.feed_key)
        .filter(FeedSource.kind == "lmarena", FeedSource.feed_key.isnot(None)).all()
    }

    legacy_link = _link()
    db.add(ExternalFeedItem(
        source_type=source.source_type, feed_key="lmarena", title="历史榜单",
        link=legacy_link, source_name="LMArena · 权威榜",
    ))
    db.commit()

    feed_ingest.backfill_source_feed_keys(db)
    db.expire_all()

    row = db.query(ExternalFeedItem).filter(ExternalFeedItem.link == legacy_link).first()
    assert row is not None
    assert row.feed_key != "lmarena", "旧 key 必须被回填掉"
    assert row.feed_key in valid_keys, f"回填后的 key 应是真实资讯源的 key：{row.feed_key}"

    db.query(ExternalFeedItem).filter(ExternalFeedItem.link == legacy_link).delete()
    db.query(FeedSource).filter(FeedSource.id == source.id).delete()
    db.commit()


def test_upsert_strips_html_from_summary(db):
    """摘要去标签：Google AI Blog 这类源会给整段 HTML，原样入库会露出 <img src=...>。"""
    link = _link()
    feed_ingest.upsert_feeds(db, [{
        "source_type": "ai_news", "feed_key": "test_html", "title": "带 HTML 摘要的资讯",
        "summary": '<p>正文一句话</p><img src="https://storage.googleapis.com/a.png">',
        "link": link, "source_name": "测试源", "meta": {}, "published_at": None,
    }])

    row = db.query(ExternalFeedItem).filter(ExternalFeedItem.link == link).first()
    assert row is not None
    assert "<" not in row.summary
    assert "正文一句话" in row.summary

    db.query(ExternalFeedItem).filter(ExternalFeedItem.link == link).delete()
    db.commit()


def test_upsert_decodes_html_entities_in_summary(db):
    """实体解码：只去标签不够，`&#8230;` / `&#8217;` 会原样进帖子正文。

    MIT Technology Review 的 description 就带数字字符引用，实测 11-06 那条
    帖子正文是「I immediately signed&#8230;」，社区里直接显示成乱码。
    """
    link = _link()
    feed_ingest.upsert_feeds(db, [{
        "source_type": "ai_news", "feed_key": "test_ent", "title": "带实体的资讯",
        "summary": "I immediately signed&#8230; and it&#8217;s done &amp;#8212; ok",
        "link": link, "source_name": "测试源", "meta": {}, "published_at": None,
    }])

    row = db.query(ExternalFeedItem).filter(ExternalFeedItem.link == link).first()
    assert row is not None
    assert "&#" not in row.summary
    assert "signed… and it’s done — ok" in row.summary

    db.query(ExternalFeedItem).filter(ExternalFeedItem.link == link).delete()
    db.commit()


def test_clean_title_strips_prefix_date_and_repeat():
    """HTML 列表页标题清洗：品类前缀 + 日期 + 主副标题重复拼接。

    实测 DeepSeek 官网的列表项原文是
    「动态2026 年 9 月 10 日DeepSeek V4.1 Flash：更强、更快、更普惠DeepSeek V4.1 Flash 正式发布」。
    """
    raw = "动态2026 年 9 月 10 日DeepSeek V4.1 Flash：更强、更快、更普惠DeepSeek V4.1 Flash 正式发布"
    cleaned = feed_ingest._clean_title(raw)
    assert cleaned == "DeepSeek V4.1 Flash：更强、更快、更普惠"

    # 干净标题原样保留
    assert feed_ingest._clean_title("我国成功发射遥感五十一号07-09星") == "我国成功发射遥感五十一号07-09星"
    # 只剥前缀与日期，不误伤正文里的数字
    assert feed_ingest._clean_title("公告2026-09-10 关于模型升级的通知") == "关于模型升级的通知"


def test_summary_echoing_title_is_dropped():
    """只复述标题的 meta description 不该进正文（央视网短消息常见）。"""
    assert feed_ingest._summary_echoes_title(
        "普速旅客列车车次变更自11月25日起实施",
        "普速旅客列车车次变更自11月25日起实施。",
    )
    # 标题之后还有实质信息 → 保留
    assert not feed_ingest._summary_echoes_title(
        "起底疯狂追星背后的隐私倒卖黑产",
        "起底疯狂追星背后的隐私倒卖黑产·四川乐山：泄露三千余名艺人信息，追星背后藏黑产链。",
    )


def test_relay_backfills_items_older_than_one_window(db, media_account):
    """回溯窗口：35 分钟之外、一周之内的未转发条目也要能补发。

    老实现只取「最近 35 分钟入库」的候选，静态源（榜单/开源榜）没有新链接，
    账号就永久静默 —— 实测开源雷达、国产模型、权威榜单三个号 0 发帖。
    """
    _acc, user = media_account
    _item(db, title="三天前入库但从未转发", minutes_ago=3 * 24 * 60)

    res = mas.relay_new_items(db)

    assert res["relayed"] >= 1
    assert _my_posts(db, user.id) == 1


def test_openrouter_source_builds_ranking_items(db, monkeypatch):
    """LMArena 不可达时的兜底源：OpenRouter 模型目录 → 长上下文模型榜。"""
    source = FeedSource(
        name="测试 OpenRouter", kind="openrouter", source_type="rankings",
        url=f"https://openrouter.ai/{uuid.uuid4().hex}", feed_key="openrouter_test_1",
        per_page=5, enabled=True, is_builtin=False,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    payload = {
        "data": [
            {"id": "a/short", "name": "A: Short", "context_length": 8000,
             "pricing": {"prompt": "0.000001", "completion": "0.000002"},
             "description": "short ctx", "created": 1700000000, "architecture": {"modality": "text->text"}},
            {"id": "b/long", "name": "B: Long", "context_length": 1000000,
             "pricing": {"prompt": "0.000003", "completion": "-1"},
             "description": "long ctx", "created": 1700000000, "architecture": {"modality": "text->text"}},
            # OpenRouter 自己的自动路由条目不是模型，必须排除
            {"id": "openrouter/auto", "name": "Auto Router", "context_length": 2000000,
             "pricing": {"prompt": "-1", "completion": "-1"}},
        ]
    }

    class _Resp:
        def json(self):
            return payload

    monkeypatch.setattr(feed_ingest, "_get", lambda *a, **k: _Resp())

    items = feed_ingest._fetch_one(db, source)

    assert len(items) == 2
    assert items[0]["title"] == "B: Long", "按上下文窗口降序，长的在前"
    assert items[0]["meta"]["context"] == 1_000_000
    assert "上下文窗口 1,000,000 tokens" in items[0]["summary"]
    assert items[0]["feed_key"] == "openrouter_test_1"

    db.query(FeedSource).filter(FeedSource.id == source.id).delete()
    db.commit()


def test_video_urls_are_not_crawled(monkeypatch):
    """视频页不爬：央视网时政源 139 条里 60 条是 tv.cctv.com 视频，没有文字稿。

    这些页面既没有 meta description 也没有正文段落，抓一次白等一次超时，
    正文最终还是空的。
    """
    assert feed_ingest.is_video_url(
        "https://tv.cctv.com/2026/11/03/VIDElBg4LMCUvTWNiyykBn7O261103.shtml"
    )
    assert feed_ingest.is_video_url("https://www.youtube.com/watch?v=abc")
    assert feed_ingest.is_video_url("https://example.com/video/123")
    # 图文新闻与普通 API 不能被误判
    assert not feed_ingest.is_video_url(
        "https://news.cctv.com/2026/11/06/ARTI0bnGcdLiQ5MBkErTzVYW261106.shtml"
    )
    assert not feed_ingest.is_video_url("https://openrouter.ai/api/v1/models")

    def _boom(*args, **kwargs):
        raise AssertionError("视频页不应发起请求")

    monkeypatch.setattr(feed_ingest, "_get", _boom)
    assert feed_ingest._fetch_article_summary(
        "https://tv.cctv.com/2026/11/03/VIDEx.shtml"
    ) is None


def test_relay_marks_video_item_instead_of_empty_body(db, media_account):
    """没摘要的视频条目：正文要说明是视频报道，不能只剩「来源 + 链接」。"""
    _acc, user = media_account
    _item(
        db,
        title="视频报道：某地迎来今冬首场降雪",
        link="https://tv.cctv.com/2026/11/03/VIDEtest0001.shtml",
    )

    mas.relay_new_items(db)

    post = (
        db.query(CommunityPost)
        .join(MediaPost, MediaPost.post_id == CommunityPost.id)
        .filter(MediaPost.account_user_id == user.id, MediaPost.kind == "relay")
        .order_by(CommunityPost.id.desc())
        .first()
    )
    assert post is not None
    assert "本条为视频报道" in post.content
    assert "来源：" in post.content

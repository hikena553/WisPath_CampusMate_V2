"""校园资讯互动（评论 / 点赞 / 转发 / 浏览）端到端测试。

覆盖范围：
- 未登录拒绝：资讯流互动接口全部要求登录；
- 批量互动状态 /interactions：只回有记录的文章，点赞态按当前用户区分；
- 详情 /articles/detail：浏览数 +1、正文抓取失败降级为 kind=error 且互动区仍可用；
- 评论增 / 查 / 删：计数同步、本人才能删、管理员可删他人；
- 点赞切换：同接口来回切换、计数正确、重复请求不重复计数；
- 转发：不去重、计数累加。

正文抓取全部 monkeypatch ``read_url``，不触网。
"""
import pytest

from app.api import campus as campus_api
from app.models.campus_social import (
    CampusArticleComment,
    CampusArticleLike,
    CampusArticleRepost,
    CampusArticleSocial,
)
from app.models.user import UserRole

ARTICLE_URL = "https://jwc.mycc.edu.cn/info/1012/9001.htm"


@pytest.fixture(autouse=True)
def _clean_social(db):
    """清理本用例涉及的文章互动数据，避免与其它用例互相污染。"""
    def _purge():
        urls = [ARTICLE_URL]
        db.query(CampusArticleComment).filter(CampusArticleComment.article_url.in_(urls)).delete(
            synchronize_session=False
        )
        db.query(CampusArticleLike).filter(CampusArticleLike.article_url.in_(urls)).delete(
            synchronize_session=False
        )
        db.query(CampusArticleRepost).filter(CampusArticleRepost.article_url.in_(urls)).delete(
            synchronize_session=False
        )
        db.query(CampusArticleSocial).filter(CampusArticleSocial.url.in_(urls)).delete(
            synchronize_session=False
        )
        db.commit()

    _purge()
    yield
    _purge()


@pytest.fixture()
def fake_reader(monkeypatch):
    """把远端抓取替换成固定正文，测试只验证我们自己的逻辑。"""
    def _fake(url: str) -> dict:
        return {
            "kind": "article",
            "title": "关于做好2026年秋季学期教学工作的通知",
            "date": "2026-10-20",
            "content_html": "<p>各位师生请注意相关安排。</p>",
            "links": [],
            "source_url": url,
        }

    monkeypatch.setattr(campus_api, "read_url", _fake)


def test_interaction_endpoints_require_login(client):
    """互动接口一律要求登录：资讯流公开，但点赞/评论要落到具体用户。"""
    assert client.get("/api/campus/interactions", params={"urls": ARTICLE_URL}).status_code == 401
    assert client.get("/api/campus/articles/detail", params={"url": ARTICLE_URL}).status_code == 401
    assert client.get("/api/campus/articles/comments", params={"url": ARTICLE_URL}).status_code == 401
    assert client.post("/api/campus/articles/like", json={"url": ARTICLE_URL}).status_code in (401, 403)


def test_detail_then_batch_interactions(api, login_token, fake_reader, db):
    """详情页浏览 +1，批量接口按当前用户返回点赞态。"""
    stu = login_token(role=UserRole.STUDENT)

    resp = api.get("/api/campus/articles/detail", headers=stu["headers"], params={"url": ARTICLE_URL})
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["article"]["kind"] == "article"
    assert detail["article"]["title"].startswith("关于做好2026年")
    assert detail["social"]["view_count"] == 1
    assert detail["social"]["liked"] is False
    assert detail["social"]["like_count"] == 0

    # 再次打开 → 浏览数继续累加
    resp = api.get("/api/campus/articles/detail", headers=stu["headers"], params={"url": ARTICLE_URL})
    assert resp.json()["social"]["view_count"] == 2

    # 点赞后批量接口能读到当前用户的点赞态
    assert api.post("/api/campus/articles/like", json={"url": ARTICLE_URL}, headers=stu["headers"]).status_code == 200
    other = login_token(role=UserRole.STUDENT)
    resp = api.get("/api/campus/interactions", headers=stu["headers"], params={"urls": ARTICLE_URL})
    assert resp.status_code == 200, resp.text
    mine = resp.json()[ARTICLE_URL]
    assert mine["liked"] is True and mine["like_count"] == 1

    resp = api.get("/api/campus/interactions", headers=other["headers"], params={"urls": ARTICLE_URL})
    theirs = resp.json()[ARTICLE_URL]
    assert theirs["liked"] is False and theirs["like_count"] == 1

    # 没有任何互动记录的文章不出现在批量结果里（前端按 0 渲染）
    resp = api.get(
        "/api/campus/interactions",
        headers=stu["headers"],
        params={"urls": "https://jwc.mycc.edu.cn/info/1012/9999.htm"},
    )
    assert resp.json() == {}


def test_detail_degrades_when_fetch_fails(api, login_token, monkeypatch):
    """正文抓取失败不应 502：降级为 kind=error，互动区仍可用。"""
    def _boom(url: str):
        raise RuntimeError("timeout")

    monkeypatch.setattr(campus_api, "read_url", _boom)
    stu = login_token(role=UserRole.STUDENT)
    resp = api.get("/api/campus/articles/detail", headers=stu["headers"], params={"url": ARTICLE_URL})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["article"]["kind"] == "error"
    assert body["article"]["content_html"] is None
    assert body["social"]["view_count"] == 1


def test_comment_create_list_delete(api, login_token, fake_reader):
    """评论增删查：计数与「本人」标记正确，他人不可删。"""
    author = login_token(role=UserRole.STUDENT)
    other = login_token(role=UserRole.STUDENT)

    resp = api.post(
        "/api/campus/articles/comments",
        json={"url": ARTICLE_URL, "content": "  这条通知很及时！  "},
        headers=author["headers"],
    )
    assert resp.status_code == 200, resp.text
    comment = resp.json()
    assert comment["content"] == "这条通知很及时！"  # 首尾空白被裁掉
    assert comment["mine"] is True
    assert comment["author_name"] == author["user"].name

    resp = api.post(
        "/api/campus/articles/comments",
        json={"url": ARTICLE_URL, "content": "同问"},
        headers=other["headers"],
    )
    second = resp.json()

    resp = api.get("/api/campus/articles/comments", headers=author["headers"], params={"url": ARTICLE_URL})
    rows = resp.json()
    assert [r["id"] for r in rows] == [comment["id"], second["id"]]  # 时间正序（楼层感）
    assert rows[0]["mine"] is True and rows[1]["mine"] is False

    resp = api.get("/api/campus/interactions", headers=author["headers"], params={"urls": ARTICLE_URL})
    assert resp.json()[ARTICLE_URL]["comment_count"] == 2

    # 他人不能删
    resp = api.delete(f"/api/campus/articles/comments/{comment['id']}", headers=other["headers"])
    assert resp.status_code == 403

    # 本人可删，计数回落
    resp = api.delete(f"/api/campus/articles/comments/{comment['id']}", headers=author["headers"])
    assert resp.status_code == 200 and resp.json()["ok"] is True
    resp = api.get("/api/campus/interactions", headers=author["headers"], params={"urls": ARTICLE_URL})
    assert resp.json()[ARTICLE_URL]["comment_count"] == 1

    # 重复删除 → 404
    resp = api.delete(f"/api/campus/articles/comments/{comment['id']}", headers=author["headers"])
    assert resp.status_code == 404


def test_admin_can_delete_others_comment(api, login_token, fake_reader):
    """社区治理：管理员可删他人评论。"""
    stu = login_token(role=UserRole.STUDENT)
    admin = login_token(role=UserRole.ADMIN)
    resp = api.post(
        "/api/campus/articles/comments",
        json={"url": ARTICLE_URL, "content": "不当内容示例"},
        headers=stu["headers"],
    )
    cid = resp.json()["id"]
    resp = api.delete(f"/api/campus/articles/comments/{cid}", headers=admin["headers"])
    assert resp.status_code == 200, resp.text


def test_comment_validation(api, login_token):
    """空内容与超长内容被拒绝。"""
    stu = login_token(role=UserRole.STUDENT)
    resp = api.post(
        "/api/campus/articles/comments",
        json={"url": ARTICLE_URL, "content": "   "},
        headers=stu["headers"],
    )
    assert resp.status_code in (400, 422)
    resp = api.post(
        "/api/campus/articles/comments",
        json={"url": ARTICLE_URL, "content": "长" * 501},
        headers=stu["headers"],
    )
    assert resp.status_code == 422


def test_like_toggle_roundtrip(api, login_token, db):
    """点赞切换：来回各一次，计数与明细表保持一致。"""
    stu = login_token(role=UserRole.STUDENT)
    first = api.post("/api/campus/articles/like", json={"url": ARTICLE_URL}, headers=stu["headers"])
    assert first.status_code == 200, first.text
    assert first.json() == {"liked": True, "count": 1}

    second = api.post("/api/campus/articles/like", json={"url": ARTICLE_URL}, headers=stu["headers"])
    assert second.json() == {"liked": False, "count": 0}

    assert db.query(CampusArticleLike).filter(CampusArticleLike.article_url == ARTICLE_URL).count() == 0


def test_like_count_is_per_user(api, login_token, db):
    """不同用户各点一次：计数为 2，明细 2 行。"""
    a = login_token(role=UserRole.STUDENT)
    b = login_token(role=UserRole.STUDENT)
    api.post("/api/campus/articles/like", json={"url": ARTICLE_URL}, headers=a["headers"])
    resp = api.post("/api/campus/articles/like", json={"url": ARTICLE_URL}, headers=b["headers"])
    assert resp.json() == {"liked": True, "count": 2}
    assert db.query(CampusArticleLike).filter(CampusArticleLike.article_url == ARTICLE_URL).count() == 2


def test_repost_accumulates(api, login_token, db):
    """转发不去重：同一用户转发两次计 2 次。"""
    stu = login_token(role=UserRole.STUDENT)
    r1 = api.post(
        "/api/campus/articles/repost",
        json={"url": ARTICLE_URL, "content": "转给室友看看"},
        headers=stu["headers"],
    )
    assert r1.status_code == 200 and r1.json()["count"] == 1
    r2 = api.post("/api/campus/articles/repost", json={"url": ARTICLE_URL}, headers=stu["headers"])
    assert r2.json()["count"] == 2
    rows = db.query(CampusArticleRepost).filter(CampusArticleRepost.article_url == ARTICLE_URL).all()
    assert len(rows) == 2
    assert rows[0].content == "转给室友看看"


def test_detail_rejects_external_url(api, login_token):
    """详情只接受校内域名：站外链接直接 400（与阅读器同一白名单）。"""
    stu = login_token(role=UserRole.STUDENT)
    resp = api.get(
        "/api/campus/articles/detail",
        headers=stu["headers"],
        params={"url": "https://example.com/a/b/c/d.html"},
    )
    assert resp.status_code == 400


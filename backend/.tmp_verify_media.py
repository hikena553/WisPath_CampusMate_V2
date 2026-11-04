"""E2E 验证脚本（临时，验证完删除）：资讯账号 CRUD / 手动发布 / 关注回显 / 登录封禁 / 转发幂等"""
import json
import urllib.request

BASE = "http://127.0.0.1:8010"


def call(method: str, path: str, token: str | None = None, body: dict | None = None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


ok = lambda cond, label: print(("PASS " if cond else "FAIL ") + label)

# 1. admin 登录
_, r = call("POST", "/api/auth/login", body={"username": "admin", "password": "admin123"})
admin = r["access_token"]
ok(bool(admin), "admin 登录")

# 2. 新增资讯账号（内容方向限定 papers）
st, r = call("POST", "/api/admin/media/accounts", admin, {
    "name": "AI 前沿观察", "signature": "跟踪 AI 论文与开源动态", "content_scope": ["papers"], "is_enabled": True,
})
ok(st == 200 and r["username"].startswith("media_"), f"新增账号 {r.get('username')} / {r.get('name')}")
acc_id = r["id"]
acc_uid = r["user_id"]

# 3. 列表 + 编辑（改名 + 启停）
st, lst = call("GET", "/api/admin/media/accounts", admin)
ok(st == 200 and len(lst) == 2, f"列表 2 个账号（含种子账号）")
st, r2 = call("PATCH", f"/api/admin/media/accounts/{acc_id}", admin, {"name": "AI 前沿观察·改", "is_enabled": False})
ok(r2["name"] == "AI 前沿观察·改" and r2["is_enabled"] is False, "编辑名称 + 停用")

# 4. 停用账号手动发布 → 应 400
st, r3 = call("POST", f"/api/admin/media/accounts/{acc_id}/publish", admin)
ok(st == 400, f"停用账号发布被拒({st})")

# 5. 启用后手动发布汇总帖
st, _ = call("PATCH", f"/api/admin/media/accounts/{acc_id}", admin, {"is_enabled": True})
st, r4 = call("POST", f"/api/admin/media/accounts/{acc_id}/publish", admin)
ok(st == 200 and (r4["posted"] or "已发布" in r4["message"]), f"手动发布: {r4.get('message')}")
st, r5 = call("POST", f"/api/admin/media/accounts/{acc_id}/publish", admin)
ok(st == 200 and not r5["posted"], f"重复发布幂等: {r5.get('message')}")

# 6. 学生登录 → 关注状态回显 + 关注/取关
_, r6 = call("POST", "/api/auth/login", body={"username": "2024001", "password": "123456"})
stu = r6["access_token"]
st, posts = call("GET", "/api/community/posts?category=%E8%B5%84%E8%AE%AF", stu)
digest_post = next((p for p in posts if p["student_id"] == acc_uid), None)
ok(digest_post is not None, f"社区「资讯」分类可见汇总帖: {digest_post['title'] if digest_post else '无'}")
ok(digest_post and digest_post["author_name"] == "AI 前沿观察·改", "作者名正确")
ok(digest_post and digest_post["author_is_following"] is False, "初始未关注")
st, rel = call("POST", f"/api/social/follow/{acc_uid}", stu)
ok(st == 200 and rel["is_following"], "关注成功")
st, posts2 = call("GET", "/api/community/posts?category=%E8%B5%84%E8%AE%AF", stu)
p2 = next((p for p in posts2 if p["student_id"] == acc_uid), None)
ok(p2 and p2["author_is_following"] is True, "帖子回显 author_is_following=true")
st, rel = call("DELETE", f"/api/social/follow/{acc_uid}", stu)
ok(st == 200 and not rel["is_following"], "取关成功")

# 7. 资讯账号登录封禁
st, r7 = call("POST", "/api/auth/login", body={"username": "media_0001", "password": "media-no-login-9527"})
ok(st == 403 and "不支持登录" in r7["detail"], f"media 登录封禁({st}): {r7.get('detail')}")

# 8. 转发链路：插一条新资讯条目 → run cycle 两次，验证只转发一次
import sys
sys.path.insert(0, ".")
from datetime import datetime, timedelta, timezone
from app.core.database import SessionLocal
from app.models.feed import ExternalFeedItem
from app.models.media import MediaPost

db = SessionLocal()
link = "https://example.com/test-relay-item-1"
db.query(ExternalFeedItem).filter(ExternalFeedItem.link == link).delete()
db.add(ExternalFeedItem(
    source_type="papers", feed_key="test", title="验证转发：Diffusion 新模型登顶榜",
    summary="这是一条用于验证转发链路的测试条目", link=link,
    source_name="arXiv", published_at=datetime.now(timezone.utc),
    created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
))
db.commit()
db.close()

from app.services.media_account_service import run_media_publish_cycle
import asyncio
s1 = asyncio.run(run_media_publish_cycle())
s2 = asyncio.run(run_media_publish_cycle())
db = SessionLocal()
cnt = db.query(MediaPost).filter(
    MediaPost.account_user_id == acc_uid, MediaPost.kind == "relay"
).count()
db.close()
ok(s1["relay"]["relayed"] >= 1 and s2["relay"]["relayed"] == 0, f"转发一轮生效/二轮幂等: {s1['relay']} → {s2['relay']}")
ok(cnt == 1, f"该账号仅 1 条转发流水(实际 {cnt})")

_, posts3 = call("GET", "/api/community/posts?category=%E8%B5%84%E8%AE%AF", stu)
relay_post = next((p for p in posts3 if "验证转发" in p["title"]), None)
ok(relay_post is not None and relay_post["student_id"] == acc_uid, "转发帖出现在社区资讯分类")

# 9. 删除账号 → 帖子一并删除
st, _ = call("DELETE", f"/api/admin/media/accounts/{acc_id}", admin)
st, posts4 = call("GET", "/api/community/posts?category=%E8%B5%84%E8%AE%AF", stu)
left = [p for p in posts4 if p["student_id"] == acc_uid]
ok(st == 200 and not left, "删号后其帖子一并清除")
db = SessionLocal()
from app.models.user import User
gone = db.query(User).filter(User.id == acc_uid).first() is None
mp = db.query(MediaPost).filter(MediaPost.account_user_id == acc_uid).count() == 0
db.close()
ok(gone and mp, "用户与发帖流水已删除")

print("\nDONE")

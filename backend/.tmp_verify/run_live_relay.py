"""在线上库跑一轮转发，验证三项修复在真实环境的产出。"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.services.media_account_service import relay_new_items  # noqa: E402

db = SessionLocal()
try:
    before = db.execute(text("select coalesce(max(id),0) from media_posts")).scalar()
    res = relay_new_items(db)
    print("relay:", res)
    rows = db.execute(
        text(
            "select u.name acc, p.title, p.content from media_posts mp "
            "join community_posts p on p.id=mp.post_id "
            "join users u on u.id=mp.account_user_id "
            "where mp.id > :m order by mp.id"
        ),
        {"m": before},
    ).fetchall()
    print(f"\n新增 {len(rows)} 条：")
    for r in rows:
        print(f"\n[{r.acc}] {r.title[:70]}")
        print("  ", (r.content or "").replace("\n", " / ")[:230])
finally:
    db.close()

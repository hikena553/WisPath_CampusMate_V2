"""实测三个「从未发帖」账号对应的资讯源能否抓到内容。"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.core.database import SessionLocal  # noqa: E402
from app.models.feed import FeedSource  # noqa: E402
from app.services.feed_ingest import _fetch_one  # noqa: E402

TARGETS = [6, 12, 18]  # DeepSeek 官方 / GitHub 最热 / LMArena

db = SessionLocal()
try:
    for sid in TARGETS:
        src = db.get(FeedSource, sid)
        if not src:
            print(f"源 {sid} 不存在")
            continue
        print(f"\n--- {src.name} (kind={src.kind}) ---")
        try:
            items = _fetch_one(db, src)
            print(f"抓到 {len(items)} 条")
            for it in items[:3]:
                print("   ", (it.get("title") or "")[:70], "|", (it.get("link") or "")[:70])
        except Exception as exc:  # noqa: BLE001 - 就是要看异常
            print(f"失败: {type(exc).__name__}: {exc}")
finally:
    db.close()

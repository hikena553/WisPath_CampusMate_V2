"""学习计划打卡连击：唯一口径。

这里集中解决三个问题，页面与智能体工具都必须从这里取数，避免口径分裂：
1. 日期口径：统一按 Asia/Shanghai 本地日计算，服务器在 UTC 时晚上打卡不会被算到第二天；
2. 连击宽限：今天还没打卡时从昨天起算，避免早上刚打开就显示断签；
3. 一日多次打卡只算一天（以日期集合去重）。
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.plan import PlanCheckin

try:
    from zoneinfo import ZoneInfo

    _LOCAL_TZ = ZoneInfo("Asia/Shanghai")
except Exception:  # pragma: no cover - 无 tzdata 的环境退化为固定 UTC+8
    _LOCAL_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


def local_today() -> date:
    """当前本地日期（Asia/Shanghai），打卡写入与查询统一用它。"""
    return datetime.now(_LOCAL_TZ).date()


def checkin_days(db: Session, student_id: int) -> set[date]:
    """该学生所有打卡日期（已去重，一天多条记录只留一天）。"""
    rows = db.query(PlanCheckin.check_date).filter(PlanCheckin.student_id == student_id).all()
    return {r[0] for r in rows if r[0]}


def compute_streak(db: Session, student_id: int, today: date | None = None) -> dict:
    """计算当前连击 / 历史最长连击 / 今日是否打卡 / 全部打卡日期。"""
    today = today or local_today()
    days = checkin_days(db, student_id)

    # 当前连续：今天未打卡则从昨天起算（1 天宽限），昨天也没打才算断签
    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)

    # 历史最长：日期排序后，相邻差 1 天即延续
    longest = 0
    run = 0
    prev: date | None = None
    for d in sorted(days):
        run = run + 1 if prev is not None and (d - prev).days == 1 else 1
        longest = max(longest, run)
        prev = d

    return {
        "current": current,
        "longest": longest,
        "today_checked": today in days,
        "days": sorted(days),
    }

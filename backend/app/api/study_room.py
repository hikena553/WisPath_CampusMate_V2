"""自习室（番茄钟）：专注计时记录的写入与今日/历史统计。

- 只记录专注（focus）会话；短休/长休不落库，避免历史列表被休息片段淹没
- 日期口径复用 plan_streak.local_today()，与打卡/连击保持同一 Asia/Shanghai 本地日
"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.study_session import StudySession
from app.models.user import User
from app.schemas.study_room import (
    StudyDayOut,
    StudyOverviewOut,
    StudySessionCreate,
    StudySessionOut,
    StudyTodayOut,
)
from app.services.plan_streak import local_today

try:
    from zoneinfo import ZoneInfo

    _LOCAL_TZ = ZoneInfo("Asia/Shanghai")
except Exception:  # pragma: no cover - 无 tzdata 环境退化为固定 UTC+8
    _LOCAL_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")

router = APIRouter(prefix="/api/study-room", tags=["自习室"])

ALLOWED_MODES = {"focus", "short_break", "long_break"}


def _naive_utc(dt: datetime | None) -> datetime | None:
    """统一存 UTC naive，读取时再按本地时区展示（避免 aware/naive 比较报错）。"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _local_hhmm(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(_LOCAL_TZ).strftime("%H:%M")


def _serialize(s: StudySession) -> StudySessionOut:
    return StudySessionOut(
        id=s.id,
        mode=s.mode,
        task_title=s.task_title,
        planned_minutes=s.planned_minutes,
        actual_minutes=s.actual_minutes,
        completed=s.completed,
        study_date=s.study_date,
        start_time=_local_hhmm(s.started_at),
        end_time=_local_hhmm(s.ended_at),
        created_at=s.created_at,
    )


@router.post("/sessions", response_model=StudySessionOut)
def create_session(
    req: StudySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存一次专注记录。实际时长以客户端计时为准，服务端只做边界校验。"""
    if req.mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail="未知的计时模式")
    if req.mode != "focus":
        raise HTTPException(status_code=400, detail="休息时段不记录专注时长")
    if not 0 <= req.actual_minutes <= 24 * 60:
        raise HTTPException(status_code=400, detail="专注时长不合法")
    if not 1 <= req.planned_minutes <= 24 * 60:
        raise HTTPException(status_code=400, detail="计划时长不合法")
    if req.actual_minutes > req.planned_minutes:
        raise HTTPException(status_code=400, detail="实际时长不能超过计划时长")

    now_utc = datetime.now(timezone.utc)
    started_at = _naive_utc(req.started_at) or _naive_utc(now_utc)
    ended_at = _naive_utc(req.ended_at) or _naive_utc(now_utc)
    session = StudySession(
        student_id=current_user.id,
        mode=req.mode,
        task_title=(req.task_title or "").strip()[:200] or None,
        planned_minutes=req.planned_minutes,
        actual_minutes=req.actual_minutes,
        completed=req.completed,
        study_date=local_today(),
        started_at=started_at,
        ended_at=ended_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _serialize(session)


@router.get("/overview", response_model=StudyOverviewOut)
def overview(
    days: int = Query(30, ge=1, le=90, description="历史统计天数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """今日专注汇总 + 近 N 天每日汇总 + 最近专注明细（按时间倒序）。"""
    today = local_today()
    start = today - timedelta(days=days - 1)
    rows = (
        db.query(StudySession)
        .filter(
            StudySession.student_id == current_user.id,
            StudySession.mode == "focus",
            StudySession.study_date >= start,
            StudySession.study_date <= today,
        )
        .order_by(StudySession.started_at.desc(), StudySession.id.desc())
        .all()
    )

    buckets: dict[date, list[StudySession]] = {}
    for r in rows:
        buckets.setdefault(r.study_date, []).append(r)

    day_list: list[StudyDayOut] = []
    for offset in range(days):
        d = start + timedelta(days=offset)
        items = buckets.get(d, [])
        day_list.append(StudyDayOut(
            date=d,
            focus_minutes=sum(i.actual_minutes for i in items),
            session_count=len(items),
        ))

    today_items = buckets.get(today, [])
    return StudyOverviewOut(
        today=StudyTodayOut(
            date=today,
            focus_minutes=sum(i.actual_minutes for i in today_items),
            session_count=len(today_items),
        ),
        days=day_list,
        sessions=[_serialize(i) for i in rows[:60]],
    )

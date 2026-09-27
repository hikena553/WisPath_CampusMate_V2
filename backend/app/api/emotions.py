"""情绪垃圾桶：通话中人脸情绪识别的记录、查询、统计与清理"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.emotion import EmotionRecord
from app.models.user import User

router = APIRouter(prefix="/api/emotions", tags=["情绪"])


def _naive_utc_now() -> datetime:
    # DB 的 DateTime 列无 timezone=True，落库后被存为 naive UTC；
    # 内存比较需与读回的 naive created_at 保持一致
    return datetime.now(timezone.utc).replace(tzinfo=None)

# face-expression-net 的 7 类情绪
EMOTION_LABELS = {
    "neutral": "平静",
    "happy": "开心",
    "sad": "难过",
    "angry": "生气",
    "fearful": "害怕",
    "disgusted": "厌恶",
    "surprised": "惊讶",
}


@router.post("/record")
def record_emotion(
    emotion: str,
    confidence: float = 0,
    source: Optional[str] = "voice_call",
    conversation_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """记录一次情绪识别结果"""
    if emotion not in EMOTION_LABELS:
        emotion = "neutral"
    rec = EmotionRecord(
        user_id=user.id,
        emotion=emotion,
        confidence=round(max(0.0, min(1.0, confidence)), 4),
        source=source,
        conversation_id=conversation_id,
    )
    db.add(rec)
    db.commit()
    return {"ok": True, "id": rec.id}


@router.post("/record/batch")
def record_emotion_batch(
    records: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量记录通话过程中的情绪（records: [{emotion, confidence}]）"""
    items = records.get("records") or []
    if not isinstance(items, list) or len(items) > 500:
        return {"ok": False, "msg": "参数不合法"}
    for it in items:
        emo = it.get("emotion", "neutral")
        if emo not in EMOTION_LABELS:
            emo = "neutral"
        db.add(EmotionRecord(
            user_id=user.id,
            emotion=emo,
            confidence=round(max(0.0, min(1.0, it.get("confidence", 0))), 4),
            source=it.get("source") or "voice_call",
            conversation_id=it.get("conversation_id"),
        ))
    db.commit()
    return {"ok": True, "count": len(items)}


@router.get("/history")
def emotion_history(
    days: int = Query(30, ge=1, le=3650),
    limit: int = Query(200, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """情绪历史记录（情绪垃圾桶回看）"""
    since = _naive_utc_now() - timedelta(days=days)
    rows = (
        db.query(EmotionRecord)
        .filter(EmotionRecord.user_id == user.id, EmotionRecord.created_at >= since)
        .order_by(EmotionRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "emotion": r.emotion,
            "label": EMOTION_LABELS.get(r.emotion, r.emotion),
            "confidence": r.confidence,
            "source": r.source,
            "conversation_id": r.conversation_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/stats")
def emotion_stats(
    days: int = Query(30, ge=1, le=3650),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """情绪垃圾桶统计：各情绪累计/占比 + 趋势"""
    since = _naive_utc_now() - timedelta(days=days)
    rows = (
        db.query(EmotionRecord)
        .filter(EmotionRecord.user_id == user.id, EmotionRecord.created_at >= since)
        .all()
    )
    stat_map = {k: 0 for k in EMOTION_LABELS}
    for r in rows:
        if r.emotion in stat_map:
            stat_map[r.emotion] += 1
    total = sum(stat_map.values())
    breakdown = [
        {
            "emotion": k,
            "label": EMOTION_LABELS[k],
            "count": v,
            "percent": round(v / total * 100, 1) if total else 0,
        }
        for k, v in stat_map.items()
    ]
    trending = []
    for i in range(0, days, 7):
        d0 = since + timedelta(days=i)
        d1 = d0 + timedelta(days=6)
        window = [r for r in rows if d0 <= r.created_at <= d1]
        if window:
            best = {}
            for r in window:
                best[r.emotion] = best.get(r.emotion, 0) + 1
            top = max(best.items(), key=lambda x: x[1])[0]
            trending.append({
                "week": d0.strftime("%m-%d"),
                "emotion": top,
                "label": EMOTION_LABELS.get(top, top),
            })
    return {"total": total, "breakdown": breakdown, "trending": trending}


@router.delete("/clear")
def clear_emotions(
    days: int = Query(3650, ge=1, le=3650),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清空情绪记录（情绪垃圾桶倒空）"""
    since = _naive_utc_now() - timedelta(days=days)
    deleted = (
        db.query(EmotionRecord)
        .filter(EmotionRecord.user_id == user.id, EmotionRecord.created_at >= since)
        .delete()
    )
    db.commit()
    return {"ok": True, "deleted": deleted}
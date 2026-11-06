import logging
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.crisis import AIDialogSummary, CrisisLevel, InterventionType
from app.schemas.crisis import (
    AIDialogSummaryOut,
    CrisisAnalyticsOut,
    CrisisInsightOut,
    CrisisResolve,
    CrisisInterveneIn,
)
from app.services import guardian_service
from app.utils.enum_helpers import safe_enum_val

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crisis", tags=["crisis"])


class CrisisConfigIn(BaseModel):
    keywords: list[str]
    notify_counselor: bool


def _filter_by_tutor(query, user, db):
    if user.role == UserRole.ADMIN:
        return query
    student_ids = [s.id for s in db.query(User).filter(User.tutor_id == user.id).all()]
    if student_ids:
        return query.filter(AIDialogSummary.student_id.in_(student_ids))
    return query.filter(False)


@router.get("/config")
def get_crisis_config(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """危机预警算法配置：回显当前生效的敏感词与通知开关（仅管理员）"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可查看")
    from app.services.crisis_service import (
        CRISIS_KEYWORDS,
        SETTING_NOTIFY_COUNSELOR,
        get_crisis_keywords,
    )
    from app.models.setting import SystemSetting
    notify_row = (
        db.query(SystemSetting)
        .filter(SystemSetting.key == SETTING_NOTIFY_COUNSELOR)
        .first()
    )
    notify = bool(notify_row and notify_row.value == "true")
    return {
        "keywords": get_crisis_keywords(db),
        "notify_counselor": notify,
        "default_keywords": CRISIS_KEYWORDS,
    }


@router.put("/config")
def update_crisis_config(
    req: CrisisConfigIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存危机预警算法配置：敏感词 + 自动通知开关（仅管理员）"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可设置")
    from app.services.crisis_service import (
        SETTING_CRISIS_KEYWORDS,
        SETTING_NOTIFY_COUNSELOR,
    )
    from app.models.setting import SystemSetting

    custom = [k.strip() for k in req.keywords if k and k.strip()]
    if not custom:
        raise HTTPException(status_code=400, detail="预警敏感词不能为空")
    updates = {
        SETTING_CRISIS_KEYWORDS: ",".join(custom),
        SETTING_NOTIFY_COUNSELOR: "true" if req.notify_counselor else "false",
    }
    for key, value in updates.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
    db.commit()
    return {"message": "算法配置已保存", "keywords": custom, "notify_counselor": req.notify_counselor}


def _alert_out(db: Session, a: AIDialogSummary) -> AIDialogSummaryOut:
    student = db.query(User).filter(User.id == a.student_id).first()
    return AIDialogSummaryOut(
        id=a.id,
        student_id=a.student_id,
        student_name=student.name if student else "",
        summary=a.summary,
        level=safe_enum_val(a.level),
        keywords_matched=a.keywords_matched,
        resolved=a.resolved,
        created_at=a.created_at.isoformat() if a.created_at else "",
        intervention_type=a.intervention_type.value if a.intervention_type else None,
        intervention_note=a.intervention_note,
        resolved_by=a.resolved_by,
        resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
        follow_up_date=str(a.follow_up_date) if a.follow_up_date else None,
    )


@router.get("/analytics", response_model=CrisisAnalyticsOut)
def get_crisis_analytics(
    days: int = 30,
    top_n: int = 40,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """心理预警聚合分析：等级分布 / 处置阶段 / 趋势 / 敏感词 / 处置时限。

    教师仅统计自己名下学生的预警（User.tutor_id == user.id），管理员统计全部，
    与列表接口 _filter_by_tutor 口径一致。
    """
    from app.services.crisis_service import analytics as crisis_analytics
    teacher_id = None if user.role == UserRole.ADMIN else user.id
    return crisis_analytics(db, teacher_id=teacher_id, days=days, top_n=top_n)


@router.get("/analytics/insight", response_model=CrisisInsightOut)
async def get_crisis_insight(
    days: int = 30,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """处置态势智能分析：基于聚合指标生成态势研判与今日处置建议。

    模型未配置或生成失败时回退规则化结论（source=rule），保证接口始终 200。
    """
    from app.services.crisis_service import insight as crisis_insight
    teacher_id = None if user.role == UserRole.ADMIN else user.id
    return await crisis_insight(db, teacher_id=teacher_id, days=days)


@router.get("/follow-up-due", response_model=list[AIDialogSummaryOut])
def list_follow_up_due(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """待随访列表：随访日期已到期且未办结的预警，供"待随访"视图与首页提醒使用。"""
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可查看")
    today = date.today()
    query = (
        db.query(AIDialogSummary)
        .filter(
            AIDialogSummary.resolved.is_(False),
            AIDialogSummary.follow_up_date.isnot(None),
            AIDialogSummary.follow_up_date <= today,
        )
        .order_by(AIDialogSummary.follow_up_date.asc())
    )
    query = _filter_by_tutor(query, user, db)
    return [_alert_out(db, a) for a in query.all()]


@router.get("/alerts", response_model=list[AIDialogSummaryOut])
def list_alerts(resolved: bool | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可查看")
    query = db.query(AIDialogSummary).order_by(AIDialogSummary.created_at.desc())
    query = _filter_by_tutor(query, user, db)
    if resolved is not None:
        query = query.filter(AIDialogSummary.resolved == resolved)
    return [_alert_out(db, a) for a in query.all()]


@router.get("/students/{student_id}/alerts", response_model=list[AIDialogSummaryOut])
def list_student_alerts(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可查看")
    if user.role != UserRole.ADMIN:
        student = db.query(User).filter(User.id == student_id).first()
        if not student or student.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权查看该学生的预警")
    alerts = db.query(AIDialogSummary).filter(
        AIDialogSummary.student_id == student_id
    ).order_by(AIDialogSummary.created_at.desc()).all()
    student = db.query(User).filter(User.id == student_id).first()
    return [
        AIDialogSummaryOut(
            id=a.id,
            student_id=a.student_id,
            student_name=student.name if student else "",
            summary=a.summary,
            level=safe_enum_val(a.level),
            keywords_matched=a.keywords_matched,
            resolved=a.resolved,
            created_at=a.created_at.isoformat() if a.created_at else "",
            intervention_type=a.intervention_type.value if a.intervention_type else None,
            intervention_note=a.intervention_note,
            resolved_by=a.resolved_by,
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            follow_up_date=str(a.follow_up_date) if a.follow_up_date else None,
        ) for a in alerts
    ]


@router.get("/monthly-report")
def get_monthly_report(
    month: str | None = None,
    class_group_id: int | None = None,
    days: int = 30,
    user: User = Depends(require_role(UserRole.TEACHER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """月度心理工作月报数据：等级分布 / 处置阶段 / SLA / 高频信号（按月聚合）。

    month 格式 YYYY-MM，缺省当月；class_group_id 可选，教师仅限名下学生。
    """
    from app.services.crisis_service import analytics as crisis_analytics

    if month:
        try:
            _dt = datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise HTTPException(status_code=400, detail="month 格式应为 YYYY-MM")
        now = datetime.now(timezone.utc)
        span_days = max(1, (now - _dt).days + 1)
    else:
        span_days = days

    teacher_id = None if user.role == UserRole.ADMIN else user.id
    data = crisis_analytics(db, teacher_id=teacher_id, days=span_days)

    rows = []
    if class_group_id is not None:
        if user.role != UserRole.ADMIN:
            in_class = db.query(User).filter(
                User.class_group_id == class_group_id, User.tutor_id == user.id
            ).count()
            if in_class == 0 and db.query(User).filter(User.class_group_id == class_group_id).count() > 0:
                raise HTTPException(status_code=403, detail="无权查看该班级")
        class_students = [u.id for u in db.query(User).filter(User.class_group_id == class_group_id).all()]
        alerts = db.query(AIDialogSummary).filter(AIDialogSummary.student_id.in_(class_students)).all() \
            if class_students else []
        rows = [_alert_export_row(db, a) for a in alerts
                if a.created_at and a.created_at.strftime("%Y-%m") == (month or datetime.now(timezone.utc).strftime("%Y-%m"))]
    return {
        "month": month or datetime.now(timezone.utc).strftime("%Y-%m"),
        "analytics": data.model_dump() if hasattr(data, "model_dump") else data.dict(),
        "rows": rows,
    }


@router.get("/{alert_id}/advice")
async def get_alert_advice(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI 处置建议：scheme/steps/rationale/taboo（severe 强制附 24h 面谈；模型不可用走规则）。"""
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可查看")
    alert = db.query(AIDialogSummary).filter(AIDialogSummary.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    if user.role != UserRole.ADMIN:
        s = db.query(User).filter(User.id == alert.student_id).first()
        if not s or s.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权查看该预警")
    from app.services import crisis_advisor_service
    return await crisis_advisor_service.get_advice(db, alert)


# ============================ 干预档案导出（脱敏） ============================

# 触发信号分类映射：导出与家长侧内容只出现分类，不出现敏感词原文与对话片段
_SIGNAL_CATEGORY = [
    ("极端行为信号", ("自杀", "自残", "不想活", "想死", "轻生", "了结", "割腕", "跳楼", "安眠药")),
    ("睡眠困扰", ("失眠", "睡不着", "熬夜")),
    ("情绪低落", ("抑郁", "没意思", "活着累", "撑不住", "崩溃", "绝望", "想哭", "难受", "消极")),
    ("焦虑压力", ("焦虑", "压力大", "心慌", "害怕", "紧张")),
    ("适应困扰", ("不想上学", "厌学", "逃避")),
]


def _signal_category(keywords_matched: str | None) -> str:
    """把命中敏感词归为脱敏分类，保证原始词不出库。"""
    if not keywords_matched:
        return "情绪信号"
    kws = [k.strip() for k in keywords_matched.split(",") if k.strip()]
    for category, words in _SIGNAL_CATEGORY:
        if any(any(w in kw or kw in w for w in words) for kw in kws):
            return category
    return "情绪信号"


def _alert_export_row(db: Session, a: AIDialogSummary) -> dict:
    """导出统一序列化层：物理上不含 raw_snippet 与敏感词原文。"""
    student = db.query(User).filter(User.id == a.student_id).first()
    resolver = db.query(User).filter(User.id == a.resolved_by).first() if a.resolved_by else None
    return {
        "student_name": student.name if student else "",
        "date": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
        "signal_category": _signal_category(a.keywords_matched),
        "level": {"severe": "高危", "moderate": "中度", "mild": "轻度", "normal": "正常"}.get(
            safe_enum_val(a.level) or "normal", "正常"
        ),
        "summary": (a.summary or "")[:120],
        "intervention": a.intervention_type.value if a.intervention_type else "未登记",
        "intervention_note": (a.intervention_note or "")[:120],
        "follow_up_date": str(a.follow_up_date) if a.follow_up_date else "",
        "resolved": "已闭环" if a.resolved else "未闭环",
        "resolved_at": a.resolved_at.strftime("%Y-%m-%d %H:%M") if a.resolved_at else "",
        "resolver": resolver.name if resolver else "",
    }


@router.get("/students/{student_id}/export")
def export_student_crisis_archive(
    student_id: int,
    start: str | None = None,
    end: str | None = None,
    level: str | None = None,
    intervention_type: str | None = None,
    resolved: bool | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按学生导出干预档案 Excel：支持时间范围/等级/干预类型/闭环状态筛选。

    合规：导出动作写审计日志；内容经 _alert_export_row 序列化，不含原始对话与敏感词原文。
    """
    from fastapi.responses import StreamingResponse
    import io
    from datetime import datetime as _dt
    from openpyxl import Workbook

    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可导出")
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if user.role != UserRole.ADMIN and student.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="无权导出该学生档案")

    query = db.query(AIDialogSummary).filter(AIDialogSummary.student_id == student_id)
    if start:
        try:
            query = query.filter(AIDialogSummary.created_at >= _dt.strptime(start, "%Y-%m-%d"))
        except ValueError:
            raise HTTPException(status_code=400, detail="start 格式应为 YYYY-MM-DD")
    if end:
        try:
            query = query.filter(
                AIDialogSummary.created_at < _dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="end 格式应为 YYYY-MM-DD")
    if level:
        try:
            query = query.filter(AIDialogSummary.level == CrisisLevel(level))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效等级: {level}")
    if intervention_type:
        try:
            query = query.filter(AIDialogSummary.intervention_type == InterventionType(intervention_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效干预类型: {intervention_type}")
    if resolved is not None:
        query = query.filter(AIDialogSummary.resolved == resolved)

    rows = [_alert_export_row(db, a) for a in query.order_by(AIDialogSummary.created_at.asc()).all()]

    # 审计：谁在何时导出了谁的档案、什么范围
    logger.info(
        "[AUDIT][crisis-export] teacher=%s student=%s rows=%s range=%s~%s level=%s intervention=%s resolved=%s",
        user.id, student_id, len(rows), start, end, level, intervention_type, resolved,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "干预档案"
    headers = ["学生", "时间", "触发信号分类", "等级", "摘要", "干预类型", "处置记录",
               "随访日期", "闭环状态", "闭环时间", "处置人"]
    keys = ["student_name", "date", "signal_category", "level", "summary", "intervention",
            "intervention_note", "follow_up_date", "resolved", "resolved_at", "resolver"]
    ws.append(headers)
    for r in rows:
        ws.append([r[k] for k in keys])
    # 汇总行
    ws.append([])
    ws.append([
        "汇总：共", len(rows), "条",
        f"高危 {sum(1 for r in rows if r['level'] == '高危')}",
        f"中度 {sum(1 for r in rows if r['level'] == '中度')}",
        f"已闭环 {sum(1 for r in rows if r['resolved'] == '已闭环')}",
    ])
    for col_idx, width in zip("ABCDEFGHIJK", (10, 18, 14, 8, 40, 12, 40, 12, 10, 18, 10)):
        ws.column_dimensions[col_idx].width = width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"crisis-archive-{student.name or student_id}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: int, req: CrisisResolve, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可操作")
    alert = db.query(AIDialogSummary).filter(AIDialogSummary.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    if user.role != UserRole.ADMIN:
        s = db.query(User).filter(User.id == alert.student_id).first()
        if not s or s.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权操作该预警")
    alert.resolved = req.resolved
    if req.resolved:
        alert.resolved_by = user.id
        alert.resolved_at = datetime.now(timezone.utc)
    else:
        alert.resolved_by = None
        alert.resolved_at = None
    db.commit()
    return {"message": "已更新"}


@router.post("/{alert_id}/intervene")
def intervene_alert(alert_id: int, req: CrisisInterveneIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != UserRole.TEACHER and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅教师可操作")
    alert = db.query(AIDialogSummary).filter(AIDialogSummary.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="预警记录不存在")
    if user.role != UserRole.ADMIN:
        s = db.query(User).filter(User.id == alert.student_id).first()
        if not s or s.tutor_id != user.id:
            raise HTTPException(status_code=403, detail="无权操作该预警")
    try:
        alert.intervention_type = InterventionType(req.intervention_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效干预类型: {req.intervention_type}")
    alert.intervention_note = req.intervention_note
    alert.follow_up_date = datetime.strptime(req.follow_up_date, "%Y-%m-%d").date() if req.follow_up_date else None
    alert.resolved = req.resolved
    alert.resolved_by = user.id
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    # 家校沟通挂接点（A9）：干预类型为「约谈家长」时同步生成沟通台账
    if req.intervention_type == InterventionType.PARENT_MEETING.value:
        try:
            guardian_service.create_log(
                db,
                teacher_id=user.id,
                student_id=alert.student_id,
                content_summary=(req.intervention_note or "危机干预约谈家长"),
                scene="crisis",
                channel="note",
            )
        except Exception:  # 台账失败不影响干预主流程
            logger.warning("危机约谈台账生成失败 alert=%s", alert_id, exc_info=True)
    return {"message": "干预记录已保存"}

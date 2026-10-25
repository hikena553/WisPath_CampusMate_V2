"""家校沟通接口：联系人 / 沟通台账 / 只读分享链接（家长无账号，凭 token 只读）。"""
import io
import logging
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from openpyxl import Workbook
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User, UserRole
from app.schemas.guardian import (
    ContactLogCreate,
    ContactLogImportResult,
    ContactLogOut,
    ContactLogPage,
    GuardianCreate,
    GuardianOut,
    GuardianOverview,
    GuardianUpdate,
    ShareLinkOut,
    SharedLogView,
)
from app.services import guardian_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guardians", tags=["guardians"])

_teacher_only = require_role(UserRole.TEACHER, UserRole.ADMIN)


def _assert_student_visible(db: Session, user: User, student_id: int) -> None:
    if user.role == UserRole.ADMIN:
        return
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student.tutor_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作该学生")


# ── 公开：家长只读页（无鉴权，凭 token） ───────────────────────


@router.get("/share/{token}", response_model=SharedLogView)
def view_shared_log(token: str, db: Session = Depends(get_db)):
    """家长只读访问：7 天有效、可撤销；危机类记录不会生成链接。"""
    data, err = guardian_service.resolve_shared_log(db, token)
    if err:
        detail = {
            "not_found": "链接不存在或已失效",
            "revoked": "链接已被撤销",
            "expired": "链接已过期",
        }.get(err, "链接不可用")
        raise HTTPException(status_code=404 if err == "not_found" else 410, detail=detail)
    return data


# ── 联系人 ────────────────────────────────────────────────────


@router.get("", response_model=list[GuardianOut])
def list_guardians(
    student_id: int = Query(...),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, student_id)
    return guardian_service.list_guardians(db, student_id)


@router.post("", response_model=GuardianOut)
def create_guardian(
    payload: GuardianCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, payload.student_id)
    item = guardian_service.create_guardian(
        db,
        student_id=payload.student_id,
        name=payload.name,
        relation=payload.relation,
        phone=payload.phone,
        is_primary=payload.is_primary,
        remark=payload.remark,
        actor_id=user.id,
    )
    return guardian_service.serialize_guardian(item, guardian_service.name_of(db, payload.student_id))


@router.patch("/{guardian_id}", response_model=GuardianOut)
def update_guardian(
    guardian_id: int,
    payload: GuardianUpdate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    item = guardian_service.get_guardian(db, guardian_id)
    if not item:
        raise HTTPException(status_code=404, detail="联系人不存在")
    _assert_student_visible(db, user, item.student_id)
    guardian_service.update_guardian(db, item, payload.model_dump(exclude_unset=True), actor_id=user.id)
    return guardian_service.serialize_guardian(item, guardian_service.name_of(db, item.student_id))


@router.delete("/{guardian_id}")
def delete_guardian(
    guardian_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    item = guardian_service.get_guardian(db, guardian_id)
    if not item:
        raise HTTPException(status_code=404, detail="联系人不存在")
    _assert_student_visible(db, user, item.student_id)
    guardian_service.soft_delete_guardian(db, item, actor_id=user.id)
    return {"message": "已删除"}


# ── 沟通台账 ──────────────────────────────────────────────────


@router.get("/logs", response_model=list[ContactLogOut])
def list_logs(
    student_id: int | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
    return guardian_service.list_logs(db, user.id, student_id=student_id)


@router.get("/logs/page", response_model=ContactLogPage)
def list_logs_page(
    student_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None, description="内容摘要模糊检索"),
    scene: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start: date | None = Query(default=None, description="起始日期 YYYY-MM-DD"),
    end: date | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """台账分页查询（服务端筛选 + 分页）。

    新增独立路由而非改造 /logs：旧的 /logs 返回数组，广泛被既有页面调用，
    改造成分页对象会破坏契约；这里以 /logs/page 提供筛选与分页能力。
    """
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
    items, total = guardian_service.list_logs_paged(
        db, user.id,
        student_id=student_id, keyword=keyword, scene=scene, channel=channel,
        status=status, start=start, end=end,
        limit=page_size, offset=(page - 1) * page_size,
    )
    return ContactLogPage(items=items, total=total)


@router.get("/overview", response_model=GuardianOverview)
def overview(
    days: int = Query(default=30, ge=1, le=365),
    student_id: int | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """家校沟通聚合：总量 / 场景分布 / 渠道分布 / 近 N 天趋势 / 沟通最多学生 Top5。"""
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
    return guardian_service.overview(db, user.id, days=days, student_id=student_id)


@router.post("/logs", response_model=ContactLogOut)
def create_log(
    payload: ContactLogCreate,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    _assert_student_visible(db, user, payload.student_id)
    if payload.guardian_id is not None:
        guardian = guardian_service.get_guardian(db, payload.guardian_id)
        if not guardian or guardian.student_id != payload.student_id:
            raise HTTPException(status_code=400, detail="联系人与学生不匹配")
    log = guardian_service.create_log(
        db,
        teacher_id=user.id,
        student_id=payload.student_id,
        content_summary=payload.content_summary,
        guardian_id=payload.guardian_id,
        scene=payload.scene,
        channel=payload.channel,
        send_sms_flag=payload.send_sms,
    )
    return guardian_service.serialize_log(log, guardian_service.name_of(db, payload.student_id))


@router.delete("/logs/{log_id}")
def delete_log(
    log_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    log = guardian_service.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="沟通记录不存在")
    if user.role != UserRole.ADMIN and log.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能删除本人的沟通记录")
    guardian_service.soft_delete_log(db, log, actor_id=user.id)
    return {"message": "已删除"}


# ── 导入 / 导出 ───────────────────────────────────────────────

EXPORT_HEADERS = ["学号", "姓名", "场景", "渠道", "状态", "内容摘要", "记录时间"]


def _filter_kwargs(
    student_id: int | None, keyword: str | None, scene: str | None,
    channel: str | None, status: str | None, start: date | None, end: date | None,
) -> dict:
    return {
        "student_id": student_id, "keyword": keyword, "scene": scene,
        "channel": channel, "status": status, "start": start, "end": end,
    }


@router.get("/logs/export")
def export_logs(
    student_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    scene: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """导出台账为 xlsx（与页面筛选同口径）。"""
    if student_id is not None:
        _assert_student_visible(db, user, student_id)
    rows = guardian_service.export_log_rows(
        db, user.id,
        **_filter_kwargs(student_id, keyword, scene, channel, status, start, end),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "家校沟通台账"
    ws.append(EXPORT_HEADERS)
    for r in rows:
        ws.append([
            "",
            r.get("student_name", ""),
            r.get("scene", ""),
            r.get("channel", ""),
            r.get("status", ""),
            r.get("content_summary", ""),
            (r.get("created_at") or "").replace("T", " ")[:19],
        ])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    encoded = quote("家校沟通台账.xlsx")
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/logs/import-template")
def download_import_template(user: User = Depends(_teacher_only)):
    """下载导入模板（表头与导入解析字段一一对应）。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "导入模板"
    ws.append(["学号", "姓名", "场景", "渠道", "内容摘要", "记录时间"])
    ws.append([
        "20230001", "张三", "日常关怀", "留痕",
        "电话沟通：本次月考成绩下滑，已与家长沟通学习计划。", "2026-10-01 10:00:00",
    ])
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    encoded = quote("家校沟通导入模板.xlsx")
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.post("/logs/import", response_model=ContactLogImportResult)
async def import_logs(
    file: UploadFile = File(...),
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    """导入 xlsx 台账：逐行校验（学生归属 / 必填 / 去重），返回导入结果。"""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件（.xlsx/.xls）")
    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="文件解析失败，请使用模板格式")
    ws = wb.active
    header = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    # 表头 → 字段映射（容忍学号列缺失，姓名必须存在）
    field_map = {"学号": "username", "姓名": "name", "场景": "scene", "渠道": "channel", "内容摘要": "content_summary", "记录时间": "created_at", "时间": "created_at"}
    index_map = {name: i for i, name in enumerate(header)}
    if "姓名" not in index_map:
        raise HTTPException(status_code=400, detail="表头缺少「姓名」列，请使用导入模板")

    rows: list[dict] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None or all(v is None or str(v).strip() == "" for v in row):
            continue
        item: dict = {}
        for label, field in field_map.items():
            idx = index_map.get(label)
            if idx is None or idx >= len(row):
                continue
            item[field] = row[idx]
        rows.append(item)

    result = guardian_service.import_logs(db, user.id, rows)
    return ContactLogImportResult(**result)


# ── 分享链接 ──────────────────────────────────────────────────


@router.post("/logs/{log_id}/share-link", response_model=ShareLinkOut)
def create_share_link(
    log_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    log = guardian_service.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="沟通记录不存在")
    if user.role != UserRole.ADMIN and log.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="只能为本人创建的记录生成链接")
    try:
        link = guardian_service.create_share_link(db, log, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return guardian_service.serialize_link(link)


@router.post("/share-links/{link_id}/revoke", response_model=ShareLinkOut)
def revoke_share_link(
    link_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    link = guardian_service.get_share_link(db, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="链接不存在")
    log = guardian_service.get_log(db, link.log_id)
    if log and user.role != UserRole.ADMIN and log.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权撤销该链接")
    guardian_service.revoke_share_link(db, link, actor_id=user.id)
    return guardian_service.serialize_link(link)


@router.get("/logs/{log_id}/share-link", response_model=ShareLinkOut | None)
def get_log_share_link(
    log_id: int,
    user: User = Depends(_teacher_only),
    db: Session = Depends(get_db),
):
    log = guardian_service.get_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="沟通记录不存在")
    if user.role != UserRole.ADMIN and log.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该记录的分享链接")
    links = guardian_service.list_links_for_logs(db, [log_id])
    return links.get(log_id)
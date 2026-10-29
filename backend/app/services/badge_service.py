"""勋章与等级体系。

设计要点：
- **勋章目录（BADGE_CATALOG）以代码常量维护**：勋章名称 / 图标 / 阈值 / 受众都是产品语义，
  改规则只需改代码，不必迁移数据；数据库只持久化「谁获得了哪枚勋章」。
- **按使用软件的进度和程度度量**：所有阈值都对准用户在各模块的真实使用数据
  （消息、群聊、学习事件、成长记录、关怀留痕…），而不是人工打分。
- **等级由成长值（points）实时换算**：成长值同样来自上述使用数据，天然反映活跃度，
  不额外建计数表，避免双写不一致。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.badge import UserBadge
from app.models.care_center import HomeVisitRecord, PraiseRecord
from app.models.care_record import CareRecord
from app.models.certificate import Certificate
from app.models.community import CommunityPost
from app.models.group import GroupMember, GroupMessage
from app.models.growth import GrowthRecord, StudentProject
from app.models.guardian import GuardianContactLog
from app.models.learning_event import LearningEvent
from app.models.message import Message
from app.models.plan import PlanCheckin
from app.models.teacher_portfolio import TeacherPortfolioItem
from app.models.teacher_task import TaskStatus, TeacherTask
from app.models.user import User, UserRole
from app.services import social_service
from app.services.plan_streak import compute_streak

# ══════════════════════════════════════════════════════════
# 勋章目录
#   audience: common（师生通用） / student / teacher
#   metric  : 取自 collect_metrics() 的度量键
#   tier    : bronze / silver / gold / diamond（用于勋章外观分级）
# ══════════════════════════════════════════════════════════
BADGE_CATALOG: list[dict] = [
    # ── 通用：基础徽章与陪伴活跃 ──
    # 默认徽章（default=True）：注册即拥有，不需要任何使用数据。它在勋章墙里恒为已获得，
    # 但**不落库、不参与「获得动画」** —— 它是起点徽章而不是奖励，避免新用户进来先看一段空动画。
    dict(code="bronze_base", name="青铜徽章", desc="基础徽章，注册即得，见证你的校园智能之旅", icon="🥉",
         tier="bronze", category="基础", audience="common", metric="activity", threshold=0,
         target_label="注册即得", default=True),
    dict(code="hello", name="初来报到", desc="完成首次使用，开启校园智能之旅", icon="🖐",
         tier="bronze", category="陪伴", audience="common", metric="activity", threshold=1,
         target_label="使用 1 次功能"),
    dict(code="chatter", name="小有名气", desc="累计发送 50 条消息", icon="💬",
         tier="bronze", category="互动", audience="common", metric="messages", threshold=50,
         target_label="发送 50 条消息"),
    dict(code="orator", name="妙语连珠", desc="累计发送 300 条消息", icon="🗣",
         tier="gold", category="互动", audience="common", metric="messages", threshold=300,
         target_label="发送 300 条消息"),
    dict(code="connector", name="广结善缘", desc="与 10 位不同的人聊过天", icon="🤝",
         tier="silver", category="互动", audience="common", metric="contacts", threshold=10,
         target_label="聊过 10 位联系人"),
    dict(code="team", name="群英荟萃", desc="加入至少 3 个群聊", icon="👥",
         tier="bronze", category="互动", audience="common", metric="groups", threshold=3,
         target_label="加入 3 个群聊"),
    dict(code="explorer", name="功能探索者", desc="在 20 次功能使用中留下足迹", icon="🧭",
         tier="silver", category="探索", audience="common", metric="activity", threshold=20,
         target_label="使用功能 20 次"),
    dict(code="loyal", name="长情陪伴", desc="与平台相伴 30 天", icon="📅",
         tier="gold", category="陪伴", audience="common", metric="active_days", threshold=30,
         target_label="相伴 30 天"),

    # ── 学生专属 ──
    dict(code="sprout", name="成长新芽", desc="写下第一条成长记录", icon="🌱",
         tier="bronze", category="成长", audience="student", metric="growth_records", threshold=1,
         target_label="1 条成长记录"),
    dict(code="skill", name="技能收藏家", desc="点亮 5 个技能标签", icon="🧩",
         tier="silver", category="成长", audience="student", metric="skills", threshold=5,
         target_label="5 个技能标签"),
    dict(code="maker", name="项目达人", desc="沉淀 3 段项目经历", icon="🚀",
         tier="silver", category="成长", audience="student", metric="projects", threshold=3,
         target_label="3 段项目经历"),
    dict(code="planner", name="计划执行者", desc="完成 10 次计划打卡", icon="✅",
         tier="silver", category="学习", audience="student", metric="plan_checkins", threshold=10,
         target_label="10 次计划打卡"),
    dict(code="streak7", name="七日不辍", desc="连续打卡 7 天", icon="🔥",
         tier="silver", category="学习", audience="student", metric="streak_best", threshold=7,
         target_label="连续 7 天"),
    dict(code="streak30", name="月度恒心", desc="连续打卡 30 天", icon="🗓️",
         tier="diamond", category="学习", audience="student", metric="streak_best", threshold=30,
         target_label="连续 30 天"),
    dict(code="scholar", name="荣誉之星", desc="收获 1 项证书或荣誉", icon="🏅",
         tier="gold", category="荣誉", audience="student", metric="certificates", threshold=1,
         target_label="1 项证书/荣誉"),
    dict(code="voice", name="社区发声", desc="在社区发布 3 条动态", icon="📣",
         tier="bronze", category="互动", audience="student", metric="posts", threshold=3,
         target_label="发布 3 条动态"),
    dict(code="appreciated", name="备受认可", desc="获得老师 3 次表扬", icon="👏",
         tier="gold", category="荣誉", audience="student", metric="praises_received", threshold=3,
         target_label="获得 3 次表扬"),

    # ── 教师专属 ──
    dict(code="first_care", name="初见关怀", desc="完成第一条关怀记录", icon="🫶",
         tier="bronze", category="育人", audience="teacher", metric="care_records", threshold=1,
         target_label="1 条关怀记录"),
    dict(code="home_visit", name="走进家门", desc="完成 3 次家访", icon="🏠",
         tier="silver", category="育人", audience="teacher", metric="home_visits", threshold=3,
         target_label="3 次家访"),
    dict(code="praiser", name="及时表扬", desc="送出 5 次正向激励", icon="🌻",
         tier="silver", category="育人", audience="teacher", metric="praises_given", threshold=5,
         target_label="5 次表扬"),
    dict(code="bridge", name="家校连心", desc="完成 10 条家校沟通留痕", icon="📞",
         tier="gold", category="育人", audience="teacher", metric="guardian_logs", threshold=10,
         target_label="10 条家校留痕"),
    dict(code="executor", name="雷厉风行", desc="办结 20 条待办任务", icon="⚡",
         tier="gold", category="工作", audience="teacher", metric="tasks_done", threshold=20,
         target_label="办结 20 条任务"),
    dict(code="showcase", name="教学展示", desc="在成长档案积累 5 条成果", icon="📚",
         tier="silver", category="工作", audience="teacher", metric="portfolio_items", threshold=5,
         target_label="5 条档案成果"),
    dict(code="mentor", name="桃李满园", desc="名下关注 10 位学生", icon="🎓",
         tier="diamond", category="育人", audience="teacher", metric="students", threshold=10,
         target_label="名下 10 位学生"),
]

# 等级阶梯：(成长值下限, 等级名, 一句话描述)
LEVELS: list[tuple[int, str, str]] = [
    (0, "新芽", "刚刚开启校园智能之旅"),
    (60, "幼苗", "已熟悉基础功能"),
    (180, "青苗", "稳定的日常使用者"),
    (400, "繁花", "高频使用者，活跃于多个模块"),
    (800, "硕果", "深度使用者，校园达人"),
    (1500, "领航", "资深领航者，平台典范用户"),
]

# 成长值权重：不同行为对平台理解的深浅不同，权重体现「使用的程度」
POINT_WEIGHTS: dict[str, int] = {
    "messages": 1,
    "group_messages": 1,
    "contacts": 6,
    "groups": 6,
    "events": 4,
    "active_days": 2,
    "growth_records": 10,
    "projects": 15,
    "skills": 6,
    "posts": 8,
    "plan_checkins": 6,
    "certificates": 20,
    "praises_received": 12,
    "care_records": 12,
    "home_visits": 15,
    "praises_given": 6,
    "guardian_logs": 6,
    "tasks_done": 4,
    "portfolio_items": 12,
    "students": 5,
}


def _count(db: Session, model, **filters) -> int:
    return int(db.query(func.count(model.id)).filter_by(**filters).scalar() or 0)


def _skills_count(user: User) -> int:
    raw = user.skills_json or {}
    if isinstance(raw, dict):
        skills = raw.get("skills") or []
        return len(skills) if isinstance(skills, list) else 0
    return 0


def collect_metrics(db: Session, user: User) -> dict[str, int]:
    """采集一名用户的真实使用度量（不同角色只填自己有的键，缺失键按 0 处理）。"""
    uid = user.id
    metrics: dict[str, int] = {
        "messages": _count(db, Message, sender_id=uid),
        "group_messages": _count(db, GroupMessage, sender_id=uid),
        "groups": _count(db, GroupMember, user_id=uid),
        "events": _count(db, LearningEvent, actor_id=uid),
    }

    # 好友：互相关注（2026-10 改版后好友 = 互关，不再用「聊过天」代替）
    metrics["contacts"] = len(social_service.friend_ids(db, uid))

    # 综合活跃度：消息 + 群消息 + 学情事件。学习事件的埋点覆盖有限，
    # 若单独作为阈值会把大量真实使用漏掉，故合并成「使用过多少次」的粗粒度指标。
    # 注意：它只用于解锁判定，不参与成长值加权（避免与三项明细重复计分）。
    metrics["activity"] = metrics["messages"] + metrics["group_messages"] + metrics["events"]

    # 相伴天数：以最早一次使用行为为起点
    first_event = db.query(func.min(LearningEvent.occurred_at)).filter(
        LearningEvent.actor_id == uid
    ).scalar()
    first_message = db.query(func.min(Message.created_at)).filter(
        Message.sender_id == uid
    ).scalar()
    firsts = [d for d in (first_event, first_message) if d is not None]
    if firsts:
        earliest = min(firsts)
        if earliest.tzinfo is not None:
            earliest = earliest.astimezone(timezone.utc).replace(tzinfo=None)
        metrics["active_days"] = max((datetime.now() - earliest).days + 1, 1)
    else:
        metrics["active_days"] = 0

    if user.role == UserRole.STUDENT:
        metrics.update(
            growth_records=_count(db, GrowthRecord, student_id=uid),
            projects=_count(db, StudentProject, student_id=uid),
            skills=_skills_count(user),
            posts=_count(db, CommunityPost, student_id=uid),
            plan_checkins=_count(db, PlanCheckin, student_id=uid),
            # 连击取历史最长（已达成不会因某天断签而丢失），与 /plan/streak 同口径
            streak_best=compute_streak(db, uid)["longest"],
            certificates=_count(db, Certificate, student_id=uid),
            praises_received=_count(db, PraiseRecord, student_id=uid, is_deleted=False),
        )
    elif user.role == UserRole.TEACHER:
        metrics.update(
            care_records=_count(db, CareRecord, teacher_id=uid, is_deleted=False),
            home_visits=_count(db, HomeVisitRecord, teacher_id=uid, is_deleted=False),
            praises_given=_count(db, PraiseRecord, teacher_id=uid, is_deleted=False),
            guardian_logs=_count(db, GuardianContactLog, teacher_id=uid, is_deleted=False),
            tasks_done=_count(db, TeacherTask, teacher_id=uid, status=TaskStatus.DONE),
            portfolio_items=_count(db, TeacherPortfolioItem, teacher_id=uid, is_deleted=False),
            students=_count(db, User, tutor_id=uid),
        )
    return metrics


def compute_points(metrics: dict[str, int]) -> int:
    return int(sum(POINT_WEIGHTS.get(key, 0) * value for key, value in metrics.items()))


def build_level(points: int) -> dict:
    """把成长值换算成等级：level 序号 + 称号 + 距下一级的进度。"""
    idx = 0
    for i, (floor, _name, _desc) in enumerate(LEVELS):
        if points >= floor:
            idx = i
    floor, name, desc = LEVELS[idx]
    next_points = LEVELS[idx + 1][0] if idx + 1 < len(LEVELS) else None
    if next_points is None:
        progress = 100
    else:
        span = next_points - floor
        progress = int(min(max((points - floor) / span, 0), 1) * 100) if span > 0 else 100
    return {
        "level": idx + 1,
        "name": name,
        "desc": desc,
        "points": points,
        "next_points": next_points,
        "progress": progress,
    }


def _audience_for(user: User) -> str:
    if user.role == UserRole.STUDENT:
        return "student"
    if user.role == UserRole.TEACHER:
        return "teacher"
    return "common"


def catalog_for(user: User) -> list[dict]:
    """当前用户可见的勋章定义：通用勋章 + 本角色专属勋章。"""
    audience = _audience_for(user)
    return [d for d in BADGE_CATALOG if d["audience"] in ("common", audience)]


def _badge_item(defn: dict, *, earned: bool, awarded_at=None, progress: int = 0) -> dict:
    return {
        "code": defn["code"],
        "name": defn["name"],
        "desc": defn["desc"],
        "icon": defn["icon"],
        "tier": defn["tier"],
        "category": defn["category"],
        "earned": earned,
        "awarded_at": awarded_at,
        "progress": progress,
        "target_label": defn.get("target_label", ""),
    }


def _earned_map(db: Session, user_id: int) -> dict[str, UserBadge]:
    rows = db.query(UserBadge).filter(UserBadge.user_id == user_id).all()
    return {r.badge_code: r for r in rows}


def evaluate_and_award(db: Session, user: User) -> list[dict]:
    """按当前使用数据结算勋章，返回本次新解锁的勋章（幂等：已获得的不会重复发）。"""
    metrics = collect_metrics(db, user)
    owned = _earned_map(db, user.id)
    new_items: list[dict] = []
    for defn in catalog_for(user):
        if defn.get("default"):
            # 默认徽章在勋章墙里恒为已获得（见 build_wall），无需结算与持久化
            continue
        if defn["code"] in owned:
            continue
        if metrics.get(defn["metric"], 0) >= defn["threshold"]:
            row = UserBadge(user_id=user.id, badge_code=defn["code"], seen=False)
            db.add(row)
            db.flush()
            new_items.append(_badge_item(defn, earned=True, awarded_at=row.awarded_at))
    if new_items:
        try:
            db.commit()
        except IntegrityError:
            # 并发结算（多标签页同时进入）时可能撞上 (user_id, badge_code) 唯一约束：
            # 说明另一路已经发放，回滚后按「本次无新增」返回即可，不向前端抛错。
            db.rollback()
            return []
    return new_items


def build_wall(db: Session, user: User) -> dict:
    """勋章墙：等级 + 已获得 + 未获得（带解锁进度）。"""
    metrics = collect_metrics(db, user)
    owned = _earned_map(db, user.id)
    earned: list[dict] = []
    locked: list[dict] = []
    for defn in catalog_for(user):
        row = owned.get(defn["code"])
        if row or defn.get("default"):
            # 已获得（或默认徽章）：默认徽章没有 awarded_at，排在勋章墙最前面
            earned.append(_badge_item(
                defn,
                earned=True,
                awarded_at=row.awarded_at if row else None,
                progress=100,
            ))
            continue
        current = metrics.get(defn["metric"], 0)
        threshold = defn["threshold"] or 1
        pct = int(min(current / threshold, 1) * 100)
        locked.append(_badge_item(defn, earned=False, progress=pct))
    # 时间统一取字符串前 19 位排序：DB 往返后是 naive、本会话新建的是 tz-aware，
    # 直接比较 datetime 会因 aware/naive 混用抛 TypeError。
    earned.sort(key=lambda b: "" if b["awarded_at"] is None else str(b["awarded_at"])[:19])
    return {
        "level": build_level(compute_points(metrics)),
        "earned": earned,
        "locked": locked,
        "earned_count": len(earned),
        "total_count": len(earned) + len(locked),
    }


def mark_all_seen(db: Session, user: User) -> int:
    """把当前用户所有未播放动画的勋章标记为已播放。"""
    count = db.query(UserBadge).filter(
        UserBadge.user_id == user.id, UserBadge.seen.is_(False)
    ).update({UserBadge.seen: True}, synchronize_session=False)
    db.commit()
    return int(count)


def pending_badges(db: Session, user: User) -> list[dict]:
    """尚未播放过获得动画的勋章（用于补播）。"""
    rows = db.query(UserBadge).filter(
        UserBadge.user_id == user.id, UserBadge.seen.is_(False)
    ).order_by(UserBadge.awarded_at.asc()).all()
    defs = {d["code"]: d for d in catalog_for(user)}
    return [
        _badge_item(defs[r.badge_code], earned=True, awarded_at=r.awarded_at, progress=100)
        for r in rows
        if r.badge_code in defs
    ]


# ══════════════════════════════════════════════════════════
# 个人主页聚合
# ══════════════════════════════════════════════════════════

def _stats_for(user: User, metrics: dict[str, int]) -> list[dict]:
    base = [
        {"key": "messages", "label": "消息", "value": metrics.get("messages", 0), "icon": "💬"},
        {"key": "contacts", "label": "好友", "value": metrics.get("contacts", 0), "icon": "🤝"},
        {"key": "groups", "label": "群聊", "value": metrics.get("groups", 0), "icon": "👥"},
    ]
    if user.role == UserRole.STUDENT:
        base = [
            {"key": "growth_records", "label": "成长记录", "value": metrics.get("growth_records", 0), "icon": "🌱"},
            {"key": "projects", "label": "项目经历", "value": metrics.get("projects", 0), "icon": "🚀"},
            {"key": "plan_checkins", "label": "计划打卡", "value": metrics.get("plan_checkins", 0), "icon": "✅"},
            {"key": "streak_best", "label": "最长连续", "value": metrics.get("streak_best", 0), "icon": "🔥"},
        ] + base
    elif user.role == UserRole.TEACHER:
        base = [
            {"key": "care_records", "label": "关怀记录", "value": metrics.get("care_records", 0), "icon": "🫶"},
            {"key": "students", "label": "名下学生", "value": metrics.get("students", 0), "icon": "🎓"},
            {"key": "tasks_done", "label": "办结任务", "value": metrics.get("tasks_done", 0), "icon": "⚡"},
        ] + base
    return base


def _highlights(db: Session, user: User) -> list[dict]:
    """近期亮点：取最近的角色化业务记录，最多 5 条。"""
    items: list[dict] = []
    if user.role == UserRole.STUDENT:
        for r in db.query(GrowthRecord).filter(GrowthRecord.student_id == user.id).order_by(
            GrowthRecord.date.desc()
        ).limit(3):
            items.append({"title": r.title, "subtitle": "成长记录", "date": str(r.date), "icon": "🌱"})
        for r in db.query(StudentProject).filter(StudentProject.student_id == user.id).order_by(
            StudentProject.start_date.desc()
        ).limit(2):
            items.append({"title": r.project_name, "subtitle": r.my_role or "项目经历",
                          "date": str(r.start_date), "icon": "🚀"})
        for r in db.query(PraiseRecord).filter(
            PraiseRecord.student_id == user.id, PraiseRecord.is_deleted.is_(False)
        ).order_by(PraiseRecord.created_at.desc()).limit(2):
            items.append({"title": r.reason, "subtitle": f"老师给予的{r.badge_name or '表扬'}",
                          "date": str(r.occurred_on or r.created_at.date()), "icon": "👏"})
    elif user.role == UserRole.TEACHER:
        for r in db.query(CareRecord).filter(
            CareRecord.teacher_id == user.id, CareRecord.is_deleted.is_(False)
        ).order_by(CareRecord.created_at.desc()).limit(3):
            items.append({"title": r.content[:40], "subtitle": "关怀留痕",
                          "date": str(r.created_at.date()), "icon": "🫶"})
        for r in db.query(TeacherPortfolioItem).filter(
            TeacherPortfolioItem.teacher_id == user.id, TeacherPortfolioItem.is_deleted.is_(False)
        ).order_by(TeacherPortfolioItem.created_at.desc()).limit(2):
            items.append({"title": r.title, "subtitle": "成长档案",
                          "date": str(r.occurred_on or r.created_at.date()), "icon": "📚"})
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:5]


def _mutual(db: Session, viewer: User, target: User) -> dict:
    """双方关系：群聊 / 学院等弱关系 + 关注关系（好友 = 互关）。

    关注口径与消息页通讯录、论坛完全一致（social_service.relation），
    主页上看到的「已互关」与消息页好友列表不会打架。
    """
    common_groups = 0
    has_conversation = False
    if viewer.id != target.id:
        mine = {gid for (gid,) in db.query(GroupMember.group_id).filter(GroupMember.user_id == viewer.id)}
        theirs = {gid for (gid,) in db.query(GroupMember.group_id).filter(GroupMember.user_id == target.id)}
        common_groups = len(mine & theirs)
        # 是否已建立单聊关系：仅作弱关系线索（如「曾聊过」），按钮语义改由关注关系决定
        has_conversation = db.query(Message.id).filter(
            or_(
                and_(Message.sender_id == viewer.id, Message.receiver_id == target.id),
                and_(Message.sender_id == target.id, Message.receiver_id == viewer.id),
            )
        ).first() is not None
    rel = social_service.relation(db, viewer.id, target.id)
    return {
        "same_college": bool(viewer.college and viewer.college == target.college),
        "common_groups": common_groups,
        "is_my_tutor": target.id == viewer.tutor_id,
        "is_my_student": target.tutor_id == viewer.id,
        "has_conversation": has_conversation,
        "is_following": rel["is_following"],
        "is_follower": rel["is_follower"],
        "is_friend": rel["is_friend"],
    }


def build_homepage(db: Session, viewer: User, target: User) -> dict:
    """聚合他人的个人主页数据（自己看自己也走这里，此时 mutual 全为空）。"""
    metrics = collect_metrics(db, target)
    wall = build_wall(db, target)
    follow_counts = social_service.counts(db, target.id)
    return {
        "id": target.id,
        "name": target.name,
        "role": target.role.value if hasattr(target.role, "value") else str(target.role),
        "username": target.username,
        "avatar": target.avatar,
        "signature": target.signature,
        "college": target.college,
        "class_name": target.class_name,
        "title": target.title,
        "department": target.department,
        "level": wall["level"],
        "badges": wall["earned"] + wall["locked"],
        "earned_count": wall["earned_count"],
        "total_count": wall["total_count"],
        # 关注 / 粉丝 / 好友（互关）三项公开计数：主页数字区直接展示
        "following_count": follow_counts["following"],
        "follower_count": follow_counts["followers"],
        "friend_count": follow_counts["friends"],
        "stats": _stats_for(target, metrics),
        "highlights": _highlights(db, target),
        "mutual": _mutual(db, viewer, target),
    }


def update_signature(db: Session, user: User, signature: str) -> str:
    """保存个性签名（去首尾空白，超长截断，空串视为清空）。"""
    value = (signature or "").strip()[:60]
    user.signature = value or None
    db.commit()
    db.refresh(user)
    return user.signature or ""


__all__ = [
    "BADGE_CATALOG",
    "LEVELS",
    "collect_metrics",
    "compute_points",
    "build_level",
    "catalog_for",
    "evaluate_and_award",
    "build_wall",
    "mark_all_seen",
    "pending_badges",
    "build_homepage",
    "update_signature",
]
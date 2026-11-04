"""资讯账号服务：账号 CRUD + 自动发帖管道（逐条转发 / 每日汇总）。

资讯账号是 users 表中 role=MEDIA 的记录（禁止登录），形象展示直接复用
users.name / avatar / signature；本服务在其上叠加 media_accounts 配置与
media_posts 发帖流水，并把内容投递到交流社区（community_posts，分类「资讯」）。

发帖管道由 app/tasks/periodic.py 每 30 分钟调一次 run_media_publish_cycle：
- relay_new_items：把近一周期新入库的 external_feed_items 按账号内容方向逐条转发；
- publish_digest：每日 8 点后为每个启用账号补发一条「今日重点汇总」（幂等）。

摘要导语优先走 LLM 润色（llm_service.complete），额度耗尽/未配置时降级为模板拼接，
发帖永不因 LLM 失败而中断。
"""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import generate_random_password, hash_password
from app.models.community import CommunityComment, CommunityLike, CommunityPost
from app.models.feed import ExternalFeedItem
from app.models.media import MediaAccount, MediaPost
from app.models.notification import Notification
from app.models.social import Follow, ForumMessage
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# 社区帖子分类白名单里的资讯分类（与 app/api/community.py::CATEGORIES 保持一致）
MEDIA_CATEGORY = "资讯"

# 每日汇总发布时刻（本地时区）：首次扫描到达该时刻后当天补发
DIGEST_HOUR = 8
# 逐条转发扫描窗口：略大于 30 分钟抓取间隔，避免两次抓取之间漏条目
RELAY_WINDOW_MINUTES = 35
# 防刷屏：单个账号单轮转发上限
RELAY_PER_CYCLE_LIMIT = 20
# 汇总帖收录的重点条目数
DIGEST_ITEM_LIMIT = 8

# 与 feed 模块一致的资讯分类白名单（external_feed_items.source_type）
FEED_SOURCE_TYPES = {"papers", "agents", "opensource", "news", "ai_news", "rankings", "cn_ai"}

# 发帖频率（逐条转发最小间隔，分钟）白名单：0=不逐条转发，仅发每日汇总
RELAY_INTERVAL_OPTIONS = {0, 30, 60, 180, 360, 720, 1440}
DEFAULT_RELAY_INTERVAL = 30

FEED_TYPE_LABELS = {
    "papers": "AI 论文",
    "opensource": "开源项目榜",
    "agents": "智能体榜",
    "news": "时政要闻",
    "ai_news": "AI 行业",
    "rankings": "权威排行榜",
    "cn_ai": "国产模型",
}


# ==================== 账号 CRUD ====================

def _clean_scope(scope: list[str] | None) -> list[str] | None:
    """内容方向白名单校验：空列表归一为 None（=全部分类）。"""
    if not scope:
        return None
    cleaned = [s for s in scope if s in FEED_SOURCE_TYPES]
    return cleaned or None


def _clean_relay_interval(value: int | None) -> int:
    """发帖频率校验：不在白名单时回落到默认（每轮转发）。"""
    if value is None:
        return DEFAULT_RELAY_INTERVAL
    return value if value in RELAY_INTERVAL_OPTIONS else DEFAULT_RELAY_INTERVAL


def _scope_matches(scope: list[str] | None, source_type: str) -> bool:
    return not scope or source_type in scope


def _media_query(db: Session):
    return db.query(MediaAccount, User).join(User, User.id == MediaAccount.user_id)


def _account_out(db: Session, account: MediaAccount, user: User) -> dict:
    stats = (
        db.query(func.count(MediaPost.id), func.max(MediaPost.created_at))
        .filter(MediaPost.account_user_id == user.id)
        .first()
    )
    return {
        "id": account.id,
        "user_id": user.id,
        "username": user.username,
        "name": user.name,
        "avatar": user.avatar,
        "signature": user.signature,
        "is_enabled": account.is_enabled,
        "content_scope": account.content_scope,
        "relay_interval_minutes": account.relay_interval_minutes,
        "post_count": int(stats[0] or 0),
        "last_posted_at": stats[1],
        "created_at": account.created_at,
    }


def list_accounts(db: Session) -> list[dict]:
    pairs = _media_query(db).order_by(MediaAccount.id.asc()).all()
    return [_account_out(db, account, user) for account, user in pairs]


def get_account(db: Session, account_id: int) -> tuple[MediaAccount, User] | None:
    pair = _media_query(db).filter(MediaAccount.id == account_id).first()
    return (pair[0], pair[1]) if pair else None


def create_account(db: Session, data) -> dict:
    """创建资讯账号：users 记录（随机密码不外发，禁止登录）+ 配置行。"""
    # username 自动生成 media_0001 风格，撞名时顺延
    max_id = db.query(func.max(MediaAccount.id)).scalar() or 0
    for seq in range(int(max_id) + 1, int(max_id) + 100):
        username = f"media_{seq:04d}"
        if not db.query(User.id).filter(User.username == username).first():
            break
    else:
        raise ValueError("无法生成唯一账号名，请稍后重试")

    user = User(
        username=username,
        password_hash=hash_password(generate_random_password()),
        name=data.name.strip(),
        role=UserRole.MEDIA,
        avatar=(data.avatar or "").strip() or None,
        signature=(data.signature or "").strip() or None,
        password_changed=True,  # 无登录语义，避免「未修改初始密码」的提醒逻辑
    )
    account = MediaAccount(
        is_enabled=data.is_enabled,
        content_scope=_clean_scope(data.content_scope),
        relay_interval_minutes=_clean_relay_interval(data.relay_interval_minutes),
    )
    db.add(user)
    db.flush()
    account.user_id = user.id
    db.add(account)
    db.commit()
    db.refresh(account)
    return _account_out(db, account, user)


def update_account(db: Session, account: MediaAccount, user: User, data) -> dict:
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"]:
        user.name = payload["name"].strip()
    if "avatar" in payload:
        user.avatar = (payload["avatar"] or "").strip() or None
    if "signature" in payload:
        user.signature = (payload["signature"] or "").strip() or None
    if "is_enabled" in payload and payload["is_enabled"] is not None:
        account.is_enabled = bool(payload["is_enabled"])
    if "content_scope" in payload:
        account.content_scope = _clean_scope(payload["content_scope"])
    if "relay_interval_minutes" in payload:
        account.relay_interval_minutes = _clean_relay_interval(payload["relay_interval_minutes"])
    db.commit()
    db.refresh(account)
    return _account_out(db, account, user)


def _delete_author_footprints(db: Session, user_id: int) -> None:
    """删除用户在社区的帖子与全部互动痕迹（管理员删号专用，与 delete_post 同口径清理）。"""
    own_posts = db.query(CommunityPost).filter(CommunityPost.student_id == user_id).all()
    for post in own_posts:
        db.query(CommunityComment).filter(CommunityComment.post_id == post.id).delete()
        db.query(CommunityLike).filter(CommunityLike.post_id == post.id).delete()
    db.query(CommunityPost).filter(CommunityPost.student_id == user_id).delete(
        synchronize_session=False
    )
    # 在别人帖子下的评论 / 点赞：删除并回退对应计数
    for comment in db.query(CommunityComment).filter(CommunityComment.student_id == user_id).all():
        post = db.query(CommunityPost).filter(CommunityPost.id == comment.post_id).first()
        if post:
            post.comment_count = max(0, post.comment_count - 1)
        db.delete(comment)
    for like in db.query(CommunityLike).filter(CommunityLike.student_id == user_id).all():
        post = db.query(CommunityPost).filter(CommunityPost.id == like.post_id).first()
        if post:
            post.like_count = max(0, post.like_count - 1)
        db.delete(like)
    # 关注关系与互动流：保留会产生「已注销用户」空壳，一并清理
    db.query(Follow).filter(
        (Follow.follower_id == user_id) | (Follow.following_id == user_id)
    ).delete(synchronize_session=False)
    db.query(ForumMessage).filter(
        (ForumMessage.user_id == user_id) | (ForumMessage.actor_id == user_id)
    ).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.user_id == user_id).delete(
        synchronize_session=False
    )


def delete_account(db: Session, account: MediaAccount, user: User) -> None:
    """删除资讯账号：发帖流水 → 帖子与互动 → 配置 → 用户，一次事务完成。"""
    db.query(MediaPost).filter(MediaPost.account_user_id == user.id).delete(
        synchronize_session=False
    )
    _delete_author_footprints(db, user.id)
    db.delete(account)
    db.delete(user)
    db.commit()


# ==================== 发帖 ====================

def _create_post(db: Session, account_user: User, title: str, content: str) -> CommunityPost:
    post = CommunityPost(
        student_id=account_user.id,
        category=MEDIA_CATEGORY,
        title=title.strip()[:100],
        content=content.strip()[:5000],
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def _item_line(item: ExternalFeedItem) -> str:
    label = FEED_TYPE_LABELS.get(item.source_type, item.source_type)
    source = item.source_name or item.feed_key or label
    line = f"{item.title}"
    if item.summary:
        line += f"\n　{item.summary.strip()[:120]}"
    line += f"\n　来源：{source} · {label}"
    if item.link:
        line += f"\n　原文：{item.link}"
    return line


def _pick_digest_items(db: Session, scope: list[str] | None) -> list[ExternalFeedItem]:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    query = db.query(ExternalFeedItem).filter(ExternalFeedItem.created_at >= since)
    if scope:
        query = query.filter(ExternalFeedItem.source_type.in_(scope))
    return (
        query.order_by(
            ExternalFeedItem.is_highlight.desc(),
            ExternalFeedItem.published_at.desc().nullslast(),
            ExternalFeedItem.created_at.desc(),
        )
        .limit(DIGEST_ITEM_LIMIT)
        .all()
    )


async def _digest_intro(account_name: str, items: list[ExternalFeedItem]) -> str:
    """LLM 生成一句话导语；未配置/额度耗尽/超时都降级为模板句。"""
    titles = "\n".join(f"- {it.title}" for it in items)
    prompt = (
        f"你是校园资讯账号「{account_name}」。根据下面今天的重点资讯标题，"
        "写一句 40 字以内的导语，概括今日看点，不要罗列条目、不要使用 emoji 开头：\n"
        f"{titles}"
    )
    try:
        from app.services import llm_service

        intro = await asyncio.wait_for(llm_service.complete(prompt, max_tokens=120), timeout=20)
        if intro:
            return intro.strip().splitlines()[0][:80]
    except Exception as exc:  # LLM 未配置 / 403 额度耗尽 / 超时统一降级
        logger.info("[资讯账号] 导语 LLM 降级：%s", exc)
    return f"今天共整理 {len(items)} 条重点资讯，速览如下："


async def publish_digest(
    db: Session,
    account: MediaAccount,
    account_user: User,
    *,
    force: bool = False,
    target_date: date | None = None,
) -> dict:
    """为账号发一条当日重点汇总帖（幂等；force=True 覆盖当天已发的汇总）。"""
    today = target_date or datetime.now().date()
    existing = (
        db.query(MediaPost)
        .filter(
            MediaPost.account_user_id == account_user.id,
            MediaPost.kind == "digest",
            MediaPost.digest_date == today,
        )
        .first()
    )
    if existing and not force:
        return {"posted": False, "message": "该账号今日已发布过汇总帖"}

    items = _pick_digest_items(db, account.content_scope)
    if not items:
        return {"posted": False, "message": "近 24 小时无可汇总的资讯条目"}

    if existing and force:  # 覆盖发布：先清掉旧帖
        db.delete(existing)
        old_post = db.query(CommunityPost).filter(CommunityPost.id == existing.post_id).first()
        if old_post:
            db.query(CommunityComment).filter(CommunityComment.post_id == old_post.id).delete()
            db.query(CommunityLike).filter(CommunityLike.post_id == old_post.id).delete()
            db.delete(old_post)
        db.commit()

    title = f"每日资讯汇总 · {today.month}月{today.day}日"
    intro = await _digest_intro(account_user.name, items)
    body = "\n\n".join(f"{idx}. {_item_line(it)}" for idx, it in enumerate(items, 1))
    content = f"{intro}\n\n{body}\n\n—— 以上内容由 {account_user.name} 自动整理自外部资讯源"

    post = _create_post(db, account_user, title, content)
    db.add(MediaPost(
        account_user_id=account_user.id,
        post_id=post.id,
        kind="digest",
        digest_date=today,
    ))
    db.commit()
    return {"posted": True, "message": "已发布今日汇总帖", "post_id": post.id, "title": post.title}


def relay_new_items(db: Session) -> dict:
    """把近一窗口期新入库的资讯条目逐条转发给各启用账号（按内容方向过滤、唯一约束兜底）。"""
    accounts = _media_query(db).filter(
        MediaAccount.is_enabled.is_(True), User.role == UserRole.MEDIA
    ).all()
    if not accounts:
        return {"relayed": 0, "accounts": 0}

    since = datetime.now(timezone.utc) - timedelta(minutes=RELAY_WINDOW_MINUTES)
    candidates = (
        db.query(ExternalFeedItem)
        .filter(ExternalFeedItem.created_at >= since)
        .order_by(ExternalFeedItem.created_at.desc())
        .limit(200)
        .all()
    )
    if not candidates:
        return {"relayed": 0, "accounts": len(accounts)}

    relayed = 0
    now_utc = datetime.now(timezone.utc)
    for account, user in accounts:
        # 发帖频率节流：距该账号上一条转发帖不足间隔则本轮跳过（0=不逐条转发）
        interval = int(account.relay_interval_minutes or 0)
        if interval <= 0:
            continue
        cutoff = now_utc - timedelta(minutes=interval)
        recently_relayed = db.query(MediaPost.id).filter(
            MediaPost.account_user_id == user.id,
            MediaPost.kind == "relay",
            MediaPost.created_at >= cutoff,
        ).first()
        if recently_relayed:
            continue
        matched = [it for it in candidates if _scope_matches(account.content_scope, it.source_type)]
        for item in matched[:RELAY_PER_CYCLE_LIMIT]:
            # 已转发过的条目直接跳过（唯一约束兜底并发）
            if db.query(MediaPost.id).filter(
                MediaPost.account_user_id == user.id,
                MediaPost.feed_item_id == item.id,
            ).first():
                continue
            label = FEED_TYPE_LABELS.get(item.source_type, item.source_type)
            content_parts = [item.summary.strip()[:600]] if item.summary else []
            content_parts.append(f"来源：{item.source_name or item.feed_key or label} · {label}")
            if item.link:
                content_parts.append(f"原文链接：{item.link}")
            post = _create_post(db, user, item.title[:100], "\n\n".join(content_parts))
            db.add(MediaPost(
                account_user_id=user.id,
                post_id=post.id,
                feed_item_id=item.id,
                kind="relay",
            ))
            db.commit()
            relayed += 1
    return {"relayed": relayed, "accounts": len(accounts)}


async def run_media_publish_cycle() -> dict:
    """周期任务入口：逐条转发 + 到点补发每日汇总。单账号失败不影响其余账号。"""
    db = SessionLocal()
    try:
        relay_stats = relay_new_items(db)

        now = datetime.now()
        digest_posted = 0
        if now.hour >= DIGEST_HOUR:
            pairs = _media_query(db).filter(
                MediaAccount.is_enabled.is_(True), User.role == UserRole.MEDIA
            ).all()
            for account, user in pairs:
                try:
                    result = await publish_digest(db, account, user)
                    if result.get("posted"):
                        digest_posted += 1
                except Exception:
                    db.rollback()
                    logger.exception("[资讯账号] 每日汇总发布失败：%s", user.username)
        return {"relay": relay_stats, "digest_posted": digest_posted}
    finally:
        db.close()

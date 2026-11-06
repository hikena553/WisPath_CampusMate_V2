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
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import generate_random_password, hash_password
from app.models.community import CommunityComment, CommunityLike, CommunityPost
from app.models.feed import ExternalFeedItem, FeedSource
from app.models.media import MediaAccount, MediaPost, MediaSourceLink, MediaStationConfig
from app.models.notification import Notification
from app.models.social import Follow, ForumMessage
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# 社区帖子分类白名单里的资讯分类（与 app/api/community.py::CATEGORIES 保持一致）
MEDIA_CATEGORY = "资讯"

# 每日汇总发布时刻（本地时区）：首次扫描到达该时刻后当天补发
DIGEST_HOUR = 8
# 资讯站单例配置行 id
STATION_ID = 1
STATION_DEFAULT_NAME = "绵小城 AI 资讯站"
PUBLISH_MODES = {"auto", "digest", "manual"}
# 逐条转发扫描窗口：略大于 30 分钟抓取间隔，避免两次抓取之间漏条目
RELAY_WINDOW_MINUTES = 35
# 转发回溯窗口：候选不只看「上一轮刚入库的」，而是回看这么多小时内尚未转发的条目。
# 原来只有 35 分钟窗口，等于「抓取当晚没发出去的条目永久作废」：10-31 之后
# 开源雷达、国产模型、权威榜单这些源就再也没有新链接，账号一条也发不出来。
# 配合下面的「单账号单轮 1 条」，积压会按 30 分钟一条的节奏慢慢消化，不会刷屏。
RELAY_LOOKBACK_HOURS = 168
# 单账号单轮从回溯窗口里取多少条候选（只为标题去重挑一条，取小一点够用）
RELAY_CANDIDATE_SCAN = 80
# 单账号单轮转发条数上限。
# 周期任务每 30 分钟跑一次，而「发帖频率」的最小可配值是 30 分钟 —— 也就是说
# 一轮最多只该发一条。历史实现是 20，结果一个账号在同一秒里连发 20 条，
# 社区时间线被同一个号刷屏，与「距上次转发的最小间隔」这个配置语义完全相反。
RELAY_PER_CYCLE_LIMIT = 1
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
        "station_connected": account.station_connected,
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


# ==================== 移动端资讯分类（按画布二级账号） ====================

def _station_is_on(db: Session) -> bool:
    """资讯站总开关是否开启；尚未初始化配置行时视为开启。"""
    station = db.query(MediaStationConfig).filter(MediaStationConfig.id == STATION_ID).first()
    return True if station is None else bool(station.is_enabled)


def visible_account(db: Session, account_id: int) -> tuple[MediaAccount, User] | None:
    """移动端可见的资讯账号：账号启用 + 已接入资讯站 + 资讯站未停用。"""
    if not _station_is_on(db):
        return None
    pair = get_account(db, account_id)
    if not pair:
        return None
    account = pair[0]
    if not account.is_enabled or not account.station_connected:
        return None
    return pair


def account_feed_keys(db: Session, account: MediaAccount) -> set[str] | None:
    """账号可见资讯源（连接线 + 源启用）的 feed_key 集合，口径与自动发帖一致。"""
    return _linked_feed_keys(db, account)


def _account_item_count(db: Session, account: MediaAccount, feed_keys: set[str] | None) -> int:
    if feed_keys == set():
        return 0
    query = db.query(func.count(ExternalFeedItem.id))
    if feed_keys:
        query = query.filter(ExternalFeedItem.feed_key.in_(feed_keys))
    if account.content_scope:
        query = query.filter(ExternalFeedItem.source_type.in_(account.content_scope))
    return int(query.scalar() or 0)


def list_visible_accounts(db: Session) -> list[dict]:
    """移动端资讯分类：按管理员画布上的资讯账号自动分 Tab。

    仅返回「启用 + 已接入资讯站」的账号，并带上当前可见的资讯源数量与条目数，
    条数口径与 /api/feeds?account_id= 完全一致（连接线 → 资讯源 feed_key）。
    """
    if not _station_is_on(db):
        return []
    pairs = (
        _media_query(db)
        .filter(MediaAccount.is_enabled.is_(True), MediaAccount.station_connected.is_(True))
        .order_by(MediaAccount.id.asc())
        .all()
    )
    result = []
    for account, user in pairs:
        feed_keys = _linked_feed_keys(db, account)
        source_count = (
            db.query(func.count(MediaSourceLink.id))
            .join(FeedSource, FeedSource.id == MediaSourceLink.feed_source_id)
            .filter(
                MediaSourceLink.account_id == account.id,
                MediaSourceLink.enabled.is_(True),
                FeedSource.enabled.is_(True),
            )
            .scalar()
        )
        result.append({
            "id": account.id,
            "name": user.name,
            "avatar": user.avatar,
            "signature": user.signature,
            "content_scope": account.content_scope or [],
            "source_count": int(source_count or 0),
            "item_count": _account_item_count(db, account, feed_keys),
        })
    return result


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
    """删除资讯账号：连接线 → 发帖流水 → 帖子与互动 → 配置 → 用户，一次事务完成。"""
    db.query(MediaSourceLink).filter(MediaSourceLink.account_id == account.id).delete(
        synchronize_session=False
    )
    db.query(MediaPost).filter(MediaPost.account_user_id == user.id).delete(
        synchronize_session=False
    )
    _delete_author_footprints(db, user.id)
    db.delete(account)
    db.delete(user)
    db.commit()


# ==================== 资讯站（根节点）配置 ====================

def get_station_config(db: Session) -> MediaStationConfig:
    """取资讯站单例配置；首次访问自动建行，保证画布根节点永远可用。"""
    station = db.query(MediaStationConfig).filter(MediaStationConfig.id == STATION_ID).first()
    if station is None:
        station = MediaStationConfig(id=STATION_ID, name=STATION_DEFAULT_NAME)
        db.add(station)
        db.commit()
        db.refresh(station)
    return station


def _station_out(station: MediaStationConfig) -> dict:
    return {
        "id": station.id,
        "name": station.name,
        "is_enabled": station.is_enabled,
        "ingest_interval_minutes": station.ingest_interval_minutes,
        "digest_hour": station.digest_hour,
        "publish_mode": station.publish_mode,
        "description": station.description,
        "updated_at": station.updated_at,
    }


def get_station_settings(db: Session) -> dict:
    return _station_out(get_station_config(db))


def update_station_config(db: Session, data) -> dict:
    station = get_station_config(db)
    payload = data.model_dump(exclude_unset=True)
    for field in ("name", "description"):
        if field in payload and payload[field] is not None:
            setattr(station, field, payload[field].strip() or None)
    if "is_enabled" in payload and payload["is_enabled"] is not None:
        station.is_enabled = bool(payload["is_enabled"])
    if "ingest_interval_minutes" in payload and payload["ingest_interval_minutes"] is not None:
        station.ingest_interval_minutes = int(payload["ingest_interval_minutes"])
    if "digest_hour" in payload and payload["digest_hour"] is not None:
        station.digest_hour = int(payload["digest_hour"])
    if "publish_mode" in payload and payload["publish_mode"] in PUBLISH_MODES:
        station.publish_mode = payload["publish_mode"]
    db.commit()
    db.refresh(station)
    return _station_out(station)


def station_runtime_settings() -> dict:
    """后台周期任务用：独立会话读取资讯站节奏配置（读取失败回落到默认值）。"""
    db = SessionLocal()
    try:
        station = get_station_config(db)
        return {
            "is_enabled": station.is_enabled,
            "ingest_interval_minutes": station.ingest_interval_minutes,
            "digest_hour": station.digest_hour,
            "publish_mode": station.publish_mode,
        }
    except Exception:
        logger.exception("[资讯站] 读取节奏配置失败，使用默认值")
        return {
            "is_enabled": True,
            "ingest_interval_minutes": 30,
            "digest_hour": DIGEST_HOUR,
            "publish_mode": "auto",
        }
    finally:
        db.close()


# ==================== 资讯账号 ↔ 资讯站 / 资讯源 连接线 ====================

def ensure_station_graph(db: Session) -> int:
    """画布首次初始化：把校园资讯现有抓取源一次性挂到已有账号下。

    这样画布展示的就是实际在抓取的源，而不是空图。只执行一次（graph_initialized），
    管理员之后主动断开的连接不会被自动补回。
    """
    station = get_station_config(db)
    if station.graph_initialized:
        return 0
    pairs = _media_query(db).all()
    if not pairs:
        return 0  # 尚无账号，等创建账号后再初始化
    sources = (
        db.query(FeedSource)
        .filter(FeedSource.enabled.is_(True))
        .order_by(FeedSource.sort_order, FeedSource.id)
        .all()
    )
    if not sources:
        return 0  # 等内置源同步完成后再初始化
    existing = {
        (link.account_id, link.feed_source_id) for link in db.query(MediaSourceLink).all()
    }
    added = 0
    for account, _user in pairs:
        scope = account.content_scope or None
        for src in sources:
            if scope and src.source_type not in scope:
                continue
            if (account.id, src.id) in existing:
                continue
            db.add(MediaSourceLink(
                account_id=account.id,
                feed_source_id=src.id,
                name=((src.name or "资讯源")[:60]),
            ))
            existing.add((account.id, src.id))
            added += 1
    station.graph_initialized = True
    db.commit()
    if added:
        logger.info("[资讯站] 画布首次初始化，已挂载 %s 个资讯源连接", added)
    return added


def mount_new_builtin_sources(db: Session) -> int:
    """把「从未被任何账号连接过」的资讯源挂到内容方向匹配的账号下。

    画布只在首次初始化时挂载（ensure_station_graph），之后新增的内置源
    （如 LMArena 不可达后补的 OpenRouter 模型榜）不会自动出现在任何账号下，
    账号就永远拿不到内容。这里补一次增量挂载：

    - 只处理「一条连接记录都没有」的源，管理员主动断开（存在且 enabled=False）
      的连接不会被复活；
    - 账号的 content_scope 决定它该接哪类源。
    """
    pairs = _media_query(db).all()
    if not pairs:
        return 0
    sources = (
        db.query(FeedSource)
        .filter(FeedSource.enabled.is_(True))
        .order_by(FeedSource.sort_order, FeedSource.id)
        .all()
    )
    if not sources:
        return 0
    touched = {sid for (sid,) in db.query(MediaSourceLink.feed_source_id).distinct().all()}
    fresh = [s for s in sources if s.id not in touched]
    if not fresh:
        return 0

    added = 0
    for account, _user in pairs:
        scope = account.content_scope or None
        for src in fresh:
            if scope and src.source_type not in scope:
                continue
            db.add(MediaSourceLink(
                account_id=account.id,
                feed_source_id=src.id,
                name=((src.name or "资讯源")[:60]),
            ))
            added += 1
    if added:
        db.commit()
        logger.info("[资讯站] 新增资讯源已挂载到账号：%s 条连接", added)
    return added


def linked_source_ids(db: Session) -> set[int]:
    """当前真正参与抓取的资讯源 id：账号已接入资讯站，且连接线/账号/源均启用。"""
    rows = (
        db.query(MediaSourceLink.feed_source_id)
        .join(MediaAccount, MediaAccount.id == MediaSourceLink.account_id)
        .filter(
            MediaSourceLink.enabled.is_(True),
            MediaAccount.is_enabled.is_(True),
            MediaAccount.station_connected.is_(True),
        )
        .all()
    )
    return {sid for (sid,) in rows}


def set_station_connected(db: Session, account: MediaAccount, connected: bool) -> dict:
    """接入 / 断开资讯站连接线：只改连接状态，不删除账号及其内容。"""
    account.station_connected = bool(connected)
    db.commit()
    db.refresh(account)
    pair = get_account(db, account.id)
    return _account_out(db, pair[0], pair[1]) if pair else {}


def _link_out(link: MediaSourceLink, source: FeedSource) -> dict:
    return {
        "id": link.id,
        "account_id": link.account_id,
        "feed_source_id": link.feed_source_id,
        "name": link.name,
        "enabled": link.enabled,
        "source_name": source.name,
        "source_type": source.source_type,
        "source_kind": source.kind,
        "source_enabled": source.enabled,
        "feed_key": source.feed_key,
        "url": source.url,
    }


def list_source_links(db: Session, account_id: int) -> list[dict]:
    pairs = (
        db.query(MediaSourceLink, FeedSource)
        .join(FeedSource, FeedSource.id == MediaSourceLink.feed_source_id)
        .filter(MediaSourceLink.account_id == account_id)
        .order_by(MediaSourceLink.sort_order, MediaSourceLink.id)
        .all()
    )
    return [_link_out(link, source) for link, source in pairs]


def create_source_link(
    db: Session, account: MediaAccount, feed_source_id: int, name: str | None = None
) -> dict:
    source = db.query(FeedSource).filter(FeedSource.id == feed_source_id).first()
    if not source:
        raise ValueError("资讯源不存在")
    dup = (
        db.query(MediaSourceLink)
        .filter(
            MediaSourceLink.account_id == account.id,
            MediaSourceLink.feed_source_id == feed_source_id,
        )
        .first()
    )
    if dup:
        raise ValueError("该资讯源已连接到此账号，可直接重连原连接线")
    link = MediaSourceLink(
        account_id=account.id,
        feed_source_id=source.id,
        name=((name or "").strip() or source.name)[:60],
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _link_out(link, source)


def get_source_link(db: Session, link_id: int) -> tuple[MediaSourceLink, FeedSource] | None:
    pair = (
        db.query(MediaSourceLink, FeedSource)
        .join(FeedSource, FeedSource.id == MediaSourceLink.feed_source_id)
        .filter(MediaSourceLink.id == link_id)
        .first()
    )
    return (pair[0], pair[1]) if pair else None


def update_source_link(db: Session, link: MediaSourceLink, source: FeedSource, data) -> dict:
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"]:
        link.name = payload["name"].strip()[:60]
    if "enabled" in payload and payload["enabled"] is not None:
        link.enabled = bool(payload["enabled"])
    db.commit()
    db.refresh(link)
    return _link_out(link, source)


def delete_source_link(db: Session, link: MediaSourceLink) -> None:
    """删除连接线本身；资讯源与已抓取内容不受影响。"""
    db.delete(link)
    db.commit()


def _linked_feed_keys(db: Session, account: MediaAccount) -> set[str] | None:
    """账号可用的资讯源 feed_key 集合。

    None = 该账号尚未配置任何连接线，沿用旧的内容方向（分类）过滤；
    空集合 = 连接线全部断开/源停用，该账号本轮不应转发任何内容。
    """
    rows = (
        db.query(MediaSourceLink, FeedSource)
        .join(FeedSource, FeedSource.id == MediaSourceLink.feed_source_id)
        .filter(MediaSourceLink.account_id == account.id)
        .all()
    )
    if not rows:
        return None
    return {
        source.feed_key
        for link, source in rows
        if link.enabled and source.enabled and source.feed_key
    }


def _item_allowed(account: MediaAccount, feed_keys: set[str] | None, item: ExternalFeedItem) -> bool:
    if not _scope_matches(account.content_scope, item.source_type):
        return False
    if feed_keys is not None and item.feed_key not in feed_keys:
        return False
    return True


def _norm_title(title: str) -> str:
    """标题归一化：去掉空白与标点、统一小写，用于跨源识别「同一条新闻」。

    例：`Gemini Omni 1.2 Flash: Fast and cost-effective with longer clips`
    在 DeepMind 与 Google AI Blog 两个源下标题完全一致，只差域名与摘要，
    归一化后即可判为重复。
    """
    return re.sub(r"[\W_]+", "", (title or "").lower())


def _relayed_titles(db: Session, account_user_id: int, limit: int = 500) -> set[str]:
    """该账号已逐条转发过的标题（归一化），用于跨轮次去重。"""
    rows = (
        db.query(CommunityPost.title)
        .join(MediaPost, MediaPost.post_id == CommunityPost.id)
        .filter(MediaPost.account_user_id == account_user_id, MediaPost.kind == "relay")
        .order_by(MediaPost.id.desc())
        .limit(limit)
        .all()
    )
    return {_norm_title(t) for (t,) in rows if t}



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


def _pick_digest_items(
    db: Session, scope: list[str] | None, feed_keys: set[str] | None = None
) -> list[ExternalFeedItem]:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    query = db.query(ExternalFeedItem).filter(ExternalFeedItem.created_at >= since)
    if scope:
        query = query.filter(ExternalFeedItem.source_type.in_(scope))
    if feed_keys is not None:
        # 连接线决定可用的资讯源；全部断开时集合为空 → in_([]) 命中 0 条
        query = query.filter(ExternalFeedItem.feed_key.in_(list(feed_keys)))
    rows = (
        query.order_by(
            ExternalFeedItem.is_highlight.desc(),
            # MySQL 不支持 NULLS LAST 语法；两种库在 DESC 排序时 NULL 均排在末尾
            ExternalFeedItem.published_at.desc(),
            ExternalFeedItem.created_at.desc(),
        )
        # 多取一些候选再按标题去重：同一条新闻常被两三个源同时收录，
        # 不去重的话汇总里会出现两条一模一样的标题（实测 11-06 那期就是）。
        .limit(DIGEST_ITEM_LIMIT * 4)
        .all()
    )
    return _unique_by_title(rows, DIGEST_ITEM_LIMIT)


def _unique_by_title(items: list[ExternalFeedItem], limit: int) -> list[ExternalFeedItem]:
    picked: list[ExternalFeedItem] = []
    seen: set[str] = set()
    for it in items:
        key = _norm_title(it.title)
        if key in seen:
            continue
        seen.add(key)
        picked.append(it)
        if len(picked) >= limit:
            break
    return picked


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

    items = _pick_digest_items(db, account.content_scope, _linked_feed_keys(db, account))
    if not items:
        return {"posted": False, "message": "近 24 小时无可汇总的资讯条目（请检查资讯源连接线是否已断开）"}

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


def _fill_missing_summary(db: Session, item: ExternalFeedItem) -> str | None:
    """转发前给缺摘要的网页类条目补一段导语。

    只为 news / cn_ai 两类抓详情页：它们是 HTML 列表页抓来的，本来就没有
    description；其余类型（arXiv / RSS / GitHub）入库时自带摘要。
    视频页不抓（没有文字稿），抓不到或只是复述标题都返回 None。
    """
    if item.source_type not in ("news", "cn_ai") or not item.link:
        return None
    try:
        from app.services.feed_ingest import (
            _fetch_article_summary, _summary_echoes_title, is_video_url,
        )
    except Exception:  # noqa: BLE001 - 补摘要不该阻断发帖
        return None
    if is_video_url(item.link):
        return None
    summary = _fetch_article_summary(item.link)
    if not summary or _summary_echoes_title(item.title or "", summary):
        return None
    return summary[:600]


def _is_video_link(link: str) -> bool:
    """转发正文用的视频判定（延迟 import，避免模块级循环依赖）。"""
    try:
        from app.services.feed_ingest import is_video_url
    except Exception:  # noqa: BLE001
        return False
    return is_video_url(link or "")


def relay_new_items(db: Session, window_minutes: int | None = None) -> dict:
    """把回溯窗口内尚未转发的资讯逐条转发给各启用账号（按连接线/内容方向过滤）。

    每个账号单独取候选：老实现是一份全局候选（最近 35 分钟、前 200 条）再在内存里
    按账号过滤，静态源（榜单、开源榜）永远进不了这份候选，账号就长期静默。
    现在改成「该账号可见范围内、尚未转发过的、最新的 N 条」，窗口由
    RELAY_LOOKBACK_HOURS 决定，配合单轮 1 条的上限，积压会匀速消化。
    """
    accounts = _media_query(db).filter(
        MediaAccount.is_enabled.is_(True),
        MediaAccount.station_connected.is_(True),
        User.role == UserRole.MEDIA,
    ).all()
    if not accounts:
        return {"relayed": 0, "accounts": 0}

    if window_minutes:
        since = datetime.now(timezone.utc) - timedelta(
            minutes=max(window_minutes, RELAY_WINDOW_MINUTES)
        )
    else:
        since = datetime.now(timezone.utc) - timedelta(hours=RELAY_LOOKBACK_HOURS)

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
        # 连接线决定账号可见的资讯源（未配置连接线时沿用内容方向）
        feed_keys = _linked_feed_keys(db, account)
        if feed_keys is not None and not feed_keys:
            continue  # 连接线全断，本轮无可用资讯源

        q = db.query(ExternalFeedItem).filter(ExternalFeedItem.created_at >= since)
        scope = account.content_scope or None
        if scope:
            q = q.filter(ExternalFeedItem.source_type.in_(list(scope)))
        if feed_keys is not None:
            q = q.filter(ExternalFeedItem.feed_key.in_(list(feed_keys)))
        # 已转发过的条目在 SQL 侧就排掉，避免窗口放宽后被大量历史条目占满候选
        relayed_ids = db.query(MediaPost.feed_item_id).filter(
            MediaPost.account_user_id == user.id,
            MediaPost.feed_item_id.isnot(None),
        )
        matched = (
            q.filter(~ExternalFeedItem.id.in_(relayed_ids))
            .order_by(ExternalFeedItem.created_at.desc(), ExternalFeedItem.id.desc())
            .limit(RELAY_CANDIDATE_SCAN)
            .all()
        )
        if not matched:
            continue

        posted_titles = _relayed_titles(db, user.id)
        # 视频条目排在图文之后（各自保持时间倒序）：视频没有文字稿，正文只能
        # 写「本条为视频报道」，能发图文就别先推视频。全是视频时照常发。
        matched.sort(key=lambda it: 1 if _is_video_link(it.link or "") else 0)
        posted = 0
        for item in matched:
            if posted >= RELAY_PER_CYCLE_LIMIT:
                break
            if not _item_allowed(account, feed_keys, item):
                continue
            # 同一条新闻常被多个源同时收录（官方博客 + 科技媒体转述），
            # 标题归一化后相同就只发一次，否则时间线上会出现两条一模一样的内容。
            if _norm_title(item.title) in posted_titles:
                continue
            label = FEED_TYPE_LABELS.get(item.source_type, item.source_type)
            # 历史条目（尤其 11-05 之前抓的时政要闻）库里没有摘要，正文会只剩
            # 「来源 + 链接」。发帖前就地补一次详情页导语，补到就回写，
            # 同一条以后不再重复请求。
            if not item.summary and item.link:
                summary = _fill_missing_summary(db, item)
                if summary:
                    item.summary = summary
            content_parts = [item.summary.strip()[:600]] if item.summary else []
            if not item.summary and item.link and _is_video_link(item.link):
                # 视频新闻没有文字稿，正文别只剩「来源 + 链接」的空壳
                content_parts.append("本条为视频报道，暂无文字摘要。")
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
            posted_titles.add(_norm_title(item.title))
            posted += 1
            relayed += 1
    return {"relayed": relayed, "accounts": len(accounts)}


async def run_media_publish_cycle() -> dict:
    """周期任务入口：按资讯站配置决定发帖模式，逐条转发 + 到点补发每日汇总。

    - 资讯站总开关关闭 → 本轮不发帖；
    - publish_mode=manual → 仅管理员手动发布；
    - publish_mode=digest → 只发每日汇总，不逐条转发；
    - publish_mode=auto → 逐条转发 + 每日汇总。
    单账号失败不影响其余账号。
    """
    db = SessionLocal()
    try:
        station = get_station_config(db)
        if not station.is_enabled or station.publish_mode == "manual":
            return {"relay": {"relayed": 0, "accounts": 0}, "digest_posted": 0, "skipped": True}

        if station.publish_mode == "digest":
            relay_stats = {"relayed": 0, "accounts": 0}
        else:
            # 抓取间隔越长，扫描窗口同步放大，避免两次抓取之间的条目被漏掉
            relay_stats = relay_new_items(
                db, window_minutes=int(station.ingest_interval_minutes or 30) + 5
            )

        now = datetime.now()
        digest_posted = 0
        if now.hour >= (station.digest_hour or DIGEST_HOUR):
            pairs = _media_query(db).filter(
                MediaAccount.is_enabled.is_(True),
                MediaAccount.station_connected.is_(True),
                User.role == UserRole.MEDIA,
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


# ==================== 画布图谱（资讯站 → 账号 → 资讯源连接） ====================

def build_graph(db: Session) -> dict:
    """一次装配画布需要的全部数据：资讯站配置、账号（含连接线）、可连接资讯源。"""
    # 先确保「校园资讯」实际抓取的内置源已入库，并完成画布首次挂载
    try:
        from app.services.feed_ingest import sync_builtin_sources

        sync_builtin_sources(db)
    except Exception:
        logger.exception("[资讯站] 同步内置资讯源失败")
        db.rollback()
    ensure_station_graph(db)
    station = get_station_config(db)

    key_counts = dict(
        db.query(ExternalFeedItem.feed_key, func.count(ExternalFeedItem.id))
        .group_by(ExternalFeedItem.feed_key)
        .all()
    )
    last_seen = dict(
        db.query(ExternalFeedItem.feed_key, func.max(ExternalFeedItem.created_at))
        .group_by(ExternalFeedItem.feed_key)
        .all()
    )

    accounts = []
    for account, user in _media_query(db).order_by(MediaAccount.id.asc()).all():
        data = _account_out(db, account, user)
        data["links"] = list_source_links(db, account.id)
        accounts.append(data)

    sources = []
    for src in db.query(FeedSource).order_by(FeedSource.sort_order, FeedSource.id).all():
        last = last_seen.get(src.feed_key) if src.feed_key else None
        sources.append({
            "id": src.id,
            "name": src.name,
            "kind": src.kind,
            "source_type": src.source_type,
            "feed_key": src.feed_key,
            "url": src.url,
            "enabled": src.enabled,
            "is_builtin": src.is_builtin,
            "item_count": int(key_counts.get(src.feed_key, 0)) if src.feed_key else 0,
            "last_ingested_at": last,
        })

    return {"station": _station_out(station), "accounts": accounts, "sources": sources}

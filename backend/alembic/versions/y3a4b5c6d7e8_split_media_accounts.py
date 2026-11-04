"""资讯账号按内容分类拆分为二级账号

Revision ID: y3a4b5c6d7e8
Revises: x2f3a4b5c6d7
Create Date: 2026-11-05

画布二级原先只有一个「绵小城资讯站」账号。现按资讯分类拆成一组二级账号
（绵小城时政小助手 / 绵小城AI前沿 / 绵小城论文速递 …），每个账号只连接
本分类的资讯源、只转发本分类内容；社区里展示的作者身份也随之变为二级账号名。

迁移只处理「仅有一个未限定内容方向的账号」这种历史形态，其它情况（管理员
已自行拆分或新建账号）直接跳过，保证可重复执行且不覆盖人工配置。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session, load_only

from app.core.security import generate_random_password, hash_password
from app.models.community import CommunityComment, CommunityLike, CommunityPost
from app.models.feed import ExternalFeedItem, FeedSource
from app.models.media import MediaAccount, MediaPost, MediaSourceLink
from app.models.user import User, UserRole

revision: str = 'y3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'x2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (资讯分类, 二级账号名, 个性签名)，顺序即画布上的默认排列顺序
CATEGORY_ACCOUNTS = [
    ("news", "绵小城时政小助手", "每天跟进时政要闻与政策动态"),
    ("ai_news", "绵小城AI前沿", "追踪 AI 行业动态与前沿进展"),
    ("papers", "绵小城论文速递", "精选 arXiv 最新 AI 论文"),
    ("opensource", "绵小城开源雷达", "GitHub / Gitee 热门开源项目"),
    ("agents", "绵小城智能体观察", "AI Agent 与智能体应用观察"),
    ("rankings", "绵小城权威榜单", "大模型权威排行榜动态"),
    ("cn_ai", "绵小城国产模型", "国产大模型动态与进展"),
]


def _next_media_username(db: Session) -> str:
    """沿用 media_0001 风格顺延生成未占用的账号名。"""
    for seq in range(1, 1000):
        username = f"media_{seq:04d}"
        if not db.query(User.id).filter(User.username == username).first():
            return username
    raise RuntimeError("无法生成唯一资讯账号名")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in ("media_accounts", "media_source_links", "media_posts", "feed_sources"):
        if not inspector.has_table(table):
            return

    with Session(bind=bind) as db:
        # 只加载本迁移实际用到的列：User 模型后续新增的列（如 qq_openid）
        # 在本迁移时尚未建表，全字段 SELECT 会因列不存在而失败。
        pairs = (
            db.query(MediaAccount, User)
            .join(User, User.id == MediaAccount.user_id)
            .options(load_only(
                User.id, User.username, User.name, User.signature,
                User.role, User.password_hash, User.password_changed,
            ))
            .all()
        )
        # 只拆分「单个账号且未限定内容方向」的历史形态
        if len(pairs) != 1:
            return
        legacy, legacy_user = pairs[0]
        if legacy.content_scope:
            return

        # 1. 建立（或复用）7 个二级账号：首个分类复用原账号，其余新建
        targets: dict[str, tuple[MediaAccount, User]] = {}
        for idx, (scope, name, signature) in enumerate(CATEGORY_ACCOUNTS):
            if idx == 0:
                legacy_user.name = name
                legacy_user.signature = signature
                legacy.content_scope = [scope]
                targets[scope] = (legacy, legacy_user)
                continue
            new_user = User(
                username=_next_media_username(db),
                password_hash=hash_password(generate_random_password()),
                name=name,
                role=UserRole.MEDIA,
                signature=signature,
                password_changed=True,
            )
            db.add(new_user)
            db.flush()
            new_account = MediaAccount(
                user_id=new_user.id,
                is_enabled=True,
                station_connected=True,
                content_scope=[scope],
                relay_interval_minutes=legacy.relay_interval_minutes,
            )
            db.add(new_account)
            db.flush()
            targets[scope] = (new_account, new_user)

        # 2. 连接线按分类重新归属：原账号只保留本分类的源
        existing = {
            (link.account_id, link.feed_source_id) for link in db.query(MediaSourceLink).all()
        }
        legacy_links = {
            link.feed_source_id: link
            for link in db.query(MediaSourceLink)
            .filter(MediaSourceLink.account_id == legacy.id)
            .all()
        }
        for source in db.query(FeedSource).all():
            target = targets.get(source.source_type)
            if not target or target[0].id == legacy.id:
                continue
            stale = legacy_links.get(source.id)
            if stale is not None:
                db.delete(stale)
                existing.discard((legacy.id, source.id))
            if (target[0].id, source.id) not in existing:
                db.add(MediaSourceLink(
                    account_id=target[0].id,
                    feed_source_id=source.id,
                    name=(source.name or "资讯源")[:60],
                ))
                existing.add((target[0].id, source.id))

        # 3. 历史帖子按分类改挂到对应二级账号，社区展示身份同步变化
        post_rows = (
            db.query(MediaPost)
            .filter(MediaPost.account_user_id == legacy_user.id)
            .all()
        )
        for row in post_rows:
            if not row.feed_item_id:
                # 旧的混合每日汇总：拆分后由各二级账号分别汇总，移除这条旧汇总
                # 先删发帖流水（media_posts.post_id 外键指向帖子），再清互动与帖子
                db.delete(row)
                db.flush()
                db.query(CommunityComment).filter(
                    CommunityComment.post_id == row.post_id
                ).delete(synchronize_session=False)
                db.query(CommunityLike).filter(
                    CommunityLike.post_id == row.post_id
                ).delete(synchronize_session=False)
                db.query(CommunityPost).filter(
                    CommunityPost.id == row.post_id
                ).delete(synchronize_session=False)
                continue
            item = db.query(ExternalFeedItem).filter(
                ExternalFeedItem.id == row.feed_item_id
            ).first()
            target = targets.get(item.source_type) if item else None
            if not target:
                continue
            row.account_user_id = target[0].user_id
            db.query(CommunityPost).filter(
                CommunityPost.id == row.post_id
            ).update({"student_id": target[0].user_id}, synchronize_session=False)

        db.flush()


def downgrade() -> None:
    """数据拆分不自动合并：降级只保留表结构，避免误删管理员后续配置。"""
    pass

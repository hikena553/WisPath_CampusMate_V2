from datetime import datetime

from pydantic import BaseModel


class BadgeItemOut(BaseModel):
    """一枚勋章的展示态：earned=False 时为「未获得」的轮廓态，附进度。"""

    code: str
    name: str
    desc: str
    icon: str
    tier: str
    category: str
    earned: bool = False
    awarded_at: datetime | None = None
    # 0-100，未获得时表示距离解锁的完成度
    progress: int = 0
    target_label: str = ""


class LevelOut(BaseModel):
    """等级：由成长值（使用活跃度）换算，供个人中心与个人主页展示。"""

    level: int
    name: str
    desc: str
    points: int
    next_points: int | None = None
    progress: int = 0


class BadgeWallOut(BaseModel):
    level: LevelOut
    earned: list[BadgeItemOut]
    locked: list[BadgeItemOut]
    earned_count: int
    total_count: int


class StatOut(BaseModel):
    key: str
    label: str
    value: int
    icon: str


class HighlightOut(BaseModel):
    title: str
    subtitle: str
    date: str
    icon: str


class MutualOut(BaseModel):
    """双方关系：用于个人主页「我们之间」信息条与关注按钮。

    2026-10 改版：好友 = 互相关注，按钮语义（关注 / 已关注 / 回关 / 取消关注）
    全部由 is_following / is_follower / is_friend 三个布尔决定。
    """

    same_college: bool = False
    common_groups: int = 0
    is_my_tutor: bool = False
    is_my_student: bool = False
    # 是否曾建立单聊（弱关系线索，仅用于展示「聊过」，不再决定按钮语义）
    has_conversation: bool = False
    # 我是否关注了 TA / TA 是否关注了我 / 是否互关（好友）
    is_following: bool = False
    is_follower: bool = False
    is_friend: bool = False


class UserHomepageOut(BaseModel):
    """个人主页：签名 / 等级 / 勋章 + 角色化数据与近期亮点。"""

    id: int
    name: str
    role: str
    username: str
    avatar: str | None = None
    signature: str | None = None
    college: str | None = None
    class_name: str | None = None
    title: str | None = None
    department: str | None = None
    level: LevelOut
    badges: list[BadgeItemOut]
    earned_count: int
    total_count: int
    # 关注 / 粉丝 / 好友（互关）三项公开计数
    following_count: int = 0
    follower_count: int = 0
    friend_count: int = 0
    stats: list[StatOut]
    highlights: list[HighlightOut]
    mutual: MutualOut


class SignatureUpdate(BaseModel):
    signature: str


class BadgeSyncOut(BaseModel):
    """同步发放结果：new 为本次新解锁的勋章，前端据此播放奖励动画。"""

    new: list[BadgeItemOut]
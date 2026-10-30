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
    """双方关系：用于个人主页「我们之间」信息条与好友操作按钮。"""

    same_college: bool = False
    common_groups: int = 0
    is_my_tutor: bool = False
    is_my_student: bool = False
    # 是否已建立单聊关系（决定主页显示「加为好友」还是「删除好友」）
    has_conversation: bool = False


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
    stats: list[StatOut]
    highlights: list[HighlightOut]
    mutual: MutualOut


class SignatureUpdate(BaseModel):
    signature: str


class BadgeSyncOut(BaseModel):
    """同步发放结果：new 为本次新解锁的勋章，前端据此播放奖励动画。"""

    new: list[BadgeItemOut]
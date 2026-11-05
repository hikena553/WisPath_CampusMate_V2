"""社交（关注 / 通讯录 / 论坛互动消息 / 好友设置）数据模型"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RelationOut(BaseModel):
    is_following: bool = False
    is_follower: bool = False
    is_friend: bool = False
    following: int = 0
    followers: int = 0
    friends: int = 0


class ContactOut(BaseModel):
    id: int
    name: str
    username: str
    avatar: str | None = None
    role: str = ""
    college: str | None = None
    class_name: str | None = None
    signature: str | None = None
    is_following: bool = False
    is_follower: bool = False
    is_friend: bool = False


class SuggestOut(BaseModel):
    id: int
    name: str
    username: str
    avatar: str | None = None
    role: str = ""
    college: str | None = None
    class_name: str | None = None
    signature: str | None = None


class ForumMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    actor_id: int
    post_id: int | None = None
    post_title: str | None = None
    # 帖子首图（没有配图时为 None，前端据此决定是否占缩略图位）
    post_cover: str | None = None
    content: str | None = None
    is_read: bool = False
    created_at: datetime
    actor_name: str = ""
    actor_avatar: str | None = None


class ForumReadIn(BaseModel):
    ids: list[int] | None = None


class FriendSettingOut(BaseModel):
    """我 → 某个人的那一份好友设置（字段含义见 models.social.FriendSetting）"""

    peer_id: int
    remark: str = ""
    care: bool = False
    mute: bool = False
    blocked: bool = False
    hide_peer_posts: bool = False
    hide_my_posts: bool = False
    intimacy: str = ""


class FriendSettingState(BaseModel):
    """主页设置页一次要的两份：我设的（mine）+ 对方设的（peer）。

    「亲密关系」这类双方共享的标识，前端只用 mine 那份写，展示时两份取其一；
    返回 peer 那份是为了让对方主页也能看到「TA 把你设为闺蜜」。
    """

    mine: FriendSettingOut
    peer: FriendSettingOut


class FriendSettingIn(BaseModel):
    """局部更新：只传要改的字段，其余保持原值（None = 不改）"""

    remark: str | None = Field(default=None, max_length=32)
    care: bool | None = None
    mute: bool | None = None
    blocked: bool | None = None
    hide_peer_posts: bool | None = None
    hide_my_posts: bool | None = None
    # 空串 = 取消亲密关系；非空必须在 INTIMACIES 之内（服务层校验）
    intimacy: str | None = Field(default=None, max_length=16)

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CampusSceneryOut(BaseModel):
    id: int
    title: str
    image_url: str
    description: str | None = None
    location: str | None = None
    area: str

    model_config = ConfigDict(from_attributes=True)


class AnnouncementOut(BaseModel):
    title: str
    date: str | None = None
    url: str | None = None


class GalleryImageOut(BaseModel):
    title: str
    image_url: str
    campus: str  # 安州 / 游仙


class CampusArticleLink(BaseModel):
    title: str
    url: str
    date: str | None = None


class CampusArticleAttachment(BaseModel):
    """正文之外的附件下载项（校站的「附件【xxx】」区块）。"""
    name: str
    url: str


class CampusArticleOut(BaseModel):
    """站内阅读器数据：文章正文或列表页链接清单"""
    kind: str  # article / links
    title: str
    date: str | None = None
    content_html: str | None = None
    links: list[CampusArticleLink] = []
    # 附件下载链接：正文容器只包含「附件：xxx」文字，真实下载地址在容器之外
    attachments: list[CampusArticleAttachment] = []
    source_url: str
    # 该页面能否用「原页渲染」（反代 + iframe）打开。
    # False 表示站点内容由 JS 注入，原页必然白屏，前端不应提供该切换选项。
    supports_original: bool = True


# ==================== 校园资讯互动（评论 / 点赞 / 转发） ====================

class CampusArticleInteractOut(BaseModel):
    """单篇资讯的互动状态。

    资讯本身来自校站爬虫、没有内部 id，故以**原文链接**作为唯一键（见 models.campus_social）。
    计数字段全部来自 campus_article_socials 汇总行，没有互动记录时为全 0。
    """
    url: str
    title: str = ""
    source: str = ""
    image_url: str | None = None
    like_count: int = 0
    favorite_count: int = 0
    comment_count: int = 0
    repost_count: int = 0
    view_count: int = 0
    liked: bool = False
    favorited: bool = False
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CampusArticleDetailOut(BaseModel):
    """文章详情：正文/链接清单（ArticleReader 同款结构）+ 互动状态。"""
    article: CampusArticleOut
    social: CampusArticleInteractOut


class CampusArticleCommentCreate(BaseModel):
    url: str = Field(..., min_length=8, max_length=700)
    content: str = Field(..., min_length=1, max_length=500)


class CampusArticleCommentOut(BaseModel):
    id: int
    article_url: str
    user_id: int
    content: str
    created_at: datetime | None = None
    author_name: str | None = None
    author_avatar: str | None = None
    # 是否本人发表：前端据此显示「删除」，也避免前端自己比对 user_id
    mine: bool = False

    model_config = ConfigDict(from_attributes=True)


class CampusArticleLikeIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=700)


class CampusArticleLikeOut(BaseModel):
    liked: bool
    count: int


class CampusArticleFavoriteIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=700)


class CampusArticleFavoriteOut(BaseModel):
    favorited: bool
    count: int


class CampusArticleRepostIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=700)
    # 附言可空：转发本身是「把这条资讯放进我的动态」的语义，附言只是可选补充
    content: str = Field("", max_length=120)


class CampusArticleRepostOut(BaseModel):
    ok: bool = True
    count: int


class OkOut(BaseModel):
    ok: bool = True


"""开源参考库：收录许可证宽松、可合法复用的成熟开源项目/模板。

设计目标（替代"逆向搬运他人项目"的合规做法）：
- 只登记许可证允许改造复用的项目，并记录「可复用范围」与「署名要求」；
- 页面脚手架生成器据此产出符合本项目规范的 Vue 骨架，并自动附上出处署名；
- license_category 用于合规分级：permissive（MIT/Apache/BSD，可商用改造）
  / weak-copyleft（LGPL/MPL，弱传染）/ copyleft（GPL 系，强传染）/ unknown。
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OpenSourceReference(Base):
    __tablename__ = "open_source_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), comment="项目/模板名称")
    repo_url: Mapped[str] = mapped_column(String(500), comment="源码仓库地址")
    homepage: Mapped[str | None] = mapped_column(String(500), default=None, comment="官网/演示地址")
    license: Mapped[str] = mapped_column(String(50), comment="许可证标识，如 MIT / Apache-2.0")
    license_category: Mapped[str] = mapped_column(
        String(20), index=True, default="permissive",
        comment="合规分级：permissive/weak-copyleft/copyleft/unknown",
    )
    stars: Mapped[int] = mapped_column(Integer, default=0, comment="收藏量（星标数），用于热度排序")
    language: Mapped[str | None] = mapped_column(String(50), default=None, comment="主要语言")
    tech_tags: Mapped[str | None] = mapped_column(String(300), default=None, comment="技术栈标签，逗号分隔")
    summary: Mapped[str | None] = mapped_column(Text, default=None, comment="项目简介")
    reusable_scope: Mapped[str | None] = mapped_column(Text, default=None, comment="可复用的范围说明")
    attribution: Mapped[str | None] = mapped_column(Text, default=None, comment="署名与许可证合规要求")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, comment="内置预设，不可删除")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

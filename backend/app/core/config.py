from os import environ
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    # 运行环境：development / production（限流 TESTING 旁路等仅开发环境生效）
    ENV: str = "development"
    # 应用运行时连接串：应对应只有 DML 权限的账号（campus_rw），无法改表结构
    DATABASE_URL: str = ""
    # 结构变更连接串：仅供 Alembic 迁移与 schema 对账使用，需 DDL 权限（campus_ddl）。
    # 留空则回落到 DATABASE_URL（单账号开发机的兼容行为）。
    MIGRATION_DATABASE_URL: str = ""
    # 启动时是否自动执行 alembic upgrade head。
    #   本地/单机可部署：True（开箱即跑）
    #   多实例/流水线发布：False，迁移由发布步骤用 campus_ddl 单独执行一次，
    #   否则 N 个副本同时 upgrade 会互相抢 DDL 锁、并让「迁移失败」变成「整个服务起不来」。
    AUTO_MIGRATE: bool = True
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LLM_API_KEY: str = ""
    # 千问 MaaS 兼容模式端点（对话/视觉/向量共用）；语音走同域名的原生接口
    LLM_BASE_URL: str = "https://maas.qianwenaiapi.com/compatible-mode/v1"
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen3.7-flash-2026-07-15"
    LLM_AGENT_MODEL: str = "qwen3.7-flash-2026-07-15"
    LLM_VISION_MODEL: str = "qwen3.8-max"
    LLM_AGENT_TEMPERATURE: float = 0.7
    LLM_AGENT_MAX_TOKENS: int = 10000
    LLM_MAX_INPUT_CHARS: int = 8000
    # AI 助手自我称谓（可在系统设置中覆盖）
    AGENT_NAME: str = "绵小城"
    # 语音合成音色（可在系统设置中覆盖）
    LLM_TTS_VOICE: str = "longanhuan_v3.6"
    # 语音播报风格提示词（可在系统设置中覆盖，作用于语音通话中大模型的回复风格）
    LLM_TTS_PROMPT: str = ""
    # 外部资讯源令牌（可选，不配置则按匿名限流抓取）
    GITHUB_TOKEN: str = ""
    GITEE_TOKEN: str = ""
    # 可观测性：日志级别（DEBUG/INFO/WARNING/ERROR）与 Sentry DSN（可选，未装 SDK 时自动跳过）
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "SECRET_KEY 未配置！请在 .env 文件中设置 JWT 签名密钥，"
                "生产环境请使用足够长且随机的字符串。"
            )
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY 强度不足：长度必须不少于 32 位。"
                "生成方式：python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if "your-secret-key" in v or v in {"changeme", "secret", "123456"}:
            raise ValueError("SECRET_KEY 疑似占位符/弱值，请更换为随机密钥后再启动。")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def check_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "DATABASE_URL 未配置！请在 .env 文件中设置数据库连接字符串。"
            )
        # 支持 SQLite 和 MySQL 格式
        if not v.startswith("sqlite") and (v.count(":") < 3 or "@" not in v):
            raise ValueError(
                "DATABASE_URL 格式错误！正确格式: sqlite:///./db.db 或 mysql+pymysql://user:password@host:port/dbname"
            )
        return v

    @field_validator("LLM_BASE_URL")
    @classmethod
    def check_llm_url(cls, v: str) -> str:
        if not v:
            raise ValueError("LLM_BASE_URL 未配置")
        return v

    @model_validator(mode="after")
    def force_migration_url_when_testing(self) -> "Settings":
        """测试态强制迁移连接串跟随 DATABASE_URL。

        为什么需要这道闸：迁移连接串是独立字段，测试如果把 DATABASE_URL 换成
        SQLite、却忘了同步换 MIGRATION_DATABASE_URL，.env 里的真实 MySQL DDL 账号
        就会被 Alembic 和 schema_guard 拿去用 —— 表现为「跑一次 pytest，生产库被
        ALTER 了一轮」。这是静默事故，没有任何报错会提示你。

        所以不依赖测试代码记得改两处，而是在配置层直接按 TESTING 常量兜死。
        """
        if environ.get("TESTING"):
            self.MIGRATION_DATABASE_URL = self.DATABASE_URL
        return self

    @property
    def llm_api_key(self) -> str:
        return self.LLM_API_KEY or environ.get("OPENAI_API_KEY", "")

    @property
    def migration_database_url(self) -> str:
        """迁移连接串：优先 MIGRATION_DATABASE_URL，未配置则回落运行时连接串。

        回落是为了兼容「单账号开发机」——但不建议生产这么做，理由见 §5 账号矩阵：
        应用进程一旦拿到 DDL 账号，任何注入点都能 DROP TABLE。
        """
        return (self.MIGRATION_DATABASE_URL or "").strip() or self.DATABASE_URL

    @property
    def uses_separate_migration_account(self) -> bool:
        """运行时与迁移是否使用不同账号（用于启动日志提示权限边界）。"""
        return self.migration_database_url != self.DATABASE_URL

    @property
    def llm_native_base(self) -> str:
        """由兼容模式端点推导原生接口根地址（TTS/ASR/多模态走 `${base}/api/v1/...`）。

        例：https://maas.qianwenaiapi.com/compatible-mode/v1 -> https://maas.qianwenaiapi.com
        修改 .env 的 LLM_BASE_URL 即可整体迁移，避免在多处硬编码域名。
        """
        base = (self.LLM_BASE_URL or "").strip().rstrip("/")
        suffix = "/compatible-mode/v1"
        if base.endswith(suffix):
            return base[: -len(suffix)]
        return base

    @property
    def is_secure(self) -> bool:
        return self.SECRET_KEY != "" and self.DATABASE_URL != ""


settings = Settings()

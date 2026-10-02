from os import environ
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # 运行环境：development / production（限流 TESTING 旁路等仅开发环境生效）
    ENV: str = "development"
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-v4-flash-0731"
    LLM_AGENT_MODEL: str = "deepseek-v4-flash-0731"
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

    @property
    def llm_api_key(self) -> str:
        return self.LLM_API_KEY or environ.get("OPENAI_API_KEY", "")

    @property
    def is_secure(self) -> bool:
        return self.SECRET_KEY != "" and self.DATABASE_URL != ""


settings = Settings()

from os import environ
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-turbo"
    LLM_AGENT_MODEL: str = "qwen-turbo"
    LLM_AGENT_TEMPERATURE: float = 0.7
    LLM_AGENT_MAX_TOKENS: int = 10000
    LLM_MAX_INPUT_CHARS: int = 8000

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
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def check_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "DATABASE_URL 未配置！请在 .env 文件中设置数据库连接字符串。"
            )
        if v.count(":") < 3 or "@" not in v:
            raise ValueError(
                "DATABASE_URL 格式错误！正确格式: mysql+pymysql://user:password@host:port/dbname"
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

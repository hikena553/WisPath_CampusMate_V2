from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 数据库 URL 统一由应用配置注入，避免在 alembic.ini 中硬编码连接凭据。
# 优先 MIGRATION_DATABASE_URL（DDL 账号 campus_ddl）：迁移要做 CREATE/ALTER/DROP，
# 运行时账号 campus_rw 没有这些权限，用它会直接 1142；未配置该变量时回落到
# DATABASE_URL，保持单账号开发机可用。
from app.core.config import settings

# ConfigParser 会把 % 当插值语法，URL 里的 %（如密码含 urlencode 字符）必须转义，
# 否则 set_main_option 抛 InterpolationSyntaxError。
config.set_main_option(
    "sqlalchemy.url", settings.migration_database_url.replace("%", "%%")
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# disable_existing_loggers=False 关键：否则迁移会禁用应用已创建的全部 logger
# （含根 logger 之外的 app.* 业务日志），导致服务启动后结构化日志静默失效。
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# add your model's MetaData object here
# for 'autogenerate' support
from app.core.database import Base
import app.models  # noqa: F401
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

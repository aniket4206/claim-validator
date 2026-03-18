import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure src/ is on the Python path so we can import claim_validator
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from claim_validator.db.session import DATABASE_URL
from claim_validator.db.models import Base

# Alembic Config object
config = context.config

# Override sqlalchemy.url from our .env-driven config
# Escape % for configparser interpolation
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our models' metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

from logging.config import fileConfig
from os import getenv
from pathlib import Path
from alembic import context
from sqlalchemy import engine_from_config, pool

def load_api_env() -> None:
    for line in (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key not in __import__("os").environ:
                __import__("os").environ[key] = value.strip().strip('"').strip("'")

load_api_env()
config = context.config
database_url = getenv(
    "ALEMBIC_DATABASE_URL",
    getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url")),
)
config.set_main_option("sqlalchemy.url", database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = None

def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
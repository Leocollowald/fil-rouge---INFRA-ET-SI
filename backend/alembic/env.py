import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from alembic import context
from sqlalchemy import create_engine, pool

from app.core.database import Base
import app.models  # noqa: F401 — importe tous les modèles pour qu'Alembic les détecte

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = os.environ["DATABASE_URL"]


def run_migrations_offline() -> None:
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

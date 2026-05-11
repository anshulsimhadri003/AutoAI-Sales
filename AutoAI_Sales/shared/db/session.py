from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from shared.bootstrap.data_seed import seed_database
from shared.config.settings import get_settings
from shared.db.base import Base

logger = logging.getLogger(__name__)

settings = get_settings()
engine_kwargs: dict = {
    "future": True,
    "pool_pre_ping": True,
}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout_seconds,
            "pool_recycle": settings.db_pool_recycle_seconds,
        }
    )

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create or migrate database tables.

    - SQLite (dev/test): uses ``create_all`` so a fresh file just works.
    - PostgreSQL + ``auto_run_migrations=True``: runs Alembic ``upgrade head``.
    - PostgreSQL + ``auto_run_migrations=False``: logs a warning if the schema
      appears empty so operators know they need to run migrations manually.
    """
    import shared.models.models  # noqa: F401 — ensure all models are registered

    is_sqlite = settings.database_url.startswith("sqlite")

    if is_sqlite:
        Base.metadata.create_all(bind=engine)
        logger.info("SQLite schema created via create_all.")
        return

    if settings.auto_run_migrations:
        _run_alembic_upgrade()
        return

    # PostgreSQL with auto_run_migrations=False — check if tables exist.
    inspector = inspect(engine)
    if not inspector.get_table_names():
        logger.warning(
            "Database has no tables and AUTO_RUN_MIGRATIONS is disabled. "
            "Run 'alembic upgrade head' before starting the app, or set "
            "AUTO_RUN_MIGRATIONS=true."
        )


def _run_alembic_upgrade() -> None:
    """Run ``alembic upgrade head`` programmatically."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations applied (upgrade head).")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_defaults() -> None:
    with SessionLocal() as db:
        seed_database(db)


def db_ready() -> bool:
    with engine.connect() as connection:
        connection.exec_driver_sql("SELECT 1")
    return True

import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()


def _build_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


def _bootstrap_existing_schema_if_needed(config: Config) -> None:
    inspector = inspect(engine)
    required_tables = {"products", "price_history", "alerts"}
    available_tables = set(inspector.get_table_names())

    has_full_schema = required_tables.issubset(available_tables)
    has_alembic_version = "alembic_version" in available_tables

    if "products" in available_tables:
        product_columns = {column["name"] for column in inspector.get_columns("products")}
        if "image_url" not in product_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR(2048)"))

    if has_full_schema and not has_alembic_version:
        # Si la base ya existe creada por create_all (fase previa),
        # la anclamos a la revision base de Alembic y luego aplicamos upgrades.
        command.stamp(config, "20260323_0001")


def init_db() -> None:
    attempts = 10
    delay_seconds = 2
    config = _build_alembic_config()

    for attempt in range(1, attempts + 1):
        try:
            _bootstrap_existing_schema_if_needed(config)
            command.upgrade(config, "head")
            return
        except OperationalError:
            if attempt == attempts:
                raise
            time.sleep(delay_seconds)

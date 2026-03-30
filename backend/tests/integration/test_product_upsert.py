from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.services.product_service import upsert_product


def test_upsert_product_updates_desired_price_for_same_url() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

    with session_factory() as session:
        first = upsert_product(session, "https://www.amazon.es/dp/B000000001", Decimal("120.00"))
        second = upsert_product(session, "https://www.amazon.es/dp/B000000001", Decimal("99.99"))

        assert first.id == second.id
        assert second.desired_price == Decimal("99.99")

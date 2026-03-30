from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.services.product_service import delete_product, list_products, upsert_product


def test_delete_product_removes_existing_row() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

    with session_factory() as session:
        product = upsert_product(session, "https://www.amazon.es/dp/B000000001", Decimal("120.00"))
        deleted = delete_product(session, product.id)

        assert deleted is True
        assert list_products(session) == []


def test_delete_product_returns_false_if_not_found() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

    with session_factory() as session:
        deleted = delete_product(session, 9999)
        assert deleted is False

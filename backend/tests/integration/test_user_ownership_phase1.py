from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import User
from app.services.product_service import list_products, upsert_product


def test_upsert_product_creates_default_owner_and_assigns_user_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

    with session_factory() as session:
        product = upsert_product(session, "https://www.amazon.es/dp/B000000002", Decimal("77.00"))
        users = list(session.scalars(select(User)).all())
        products = list_products(session)

        assert len(users) == 1
        assert product.user_id == users[0].id
        assert users[0].email
        assert len(products) == 1
        assert products[0].user_id == users[0].id

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import PriceHistory, Product, User
from app.scrapers import resolve_scraper

settings = get_settings()


def detect_store(url: str) -> str:
    scraper = resolve_scraper(url)
    if not scraper:
        raise ValueError("La URL no pertenece a una tienda soportada (Amazon ES o PCComponentes).")
    return scraper.store_code


def _default_user_email() -> str:
    email = settings.alert_email.strip().lower()
    if not email:
        raise ValueError("ALERT_EMAIL no puede estar vacio. Define un email valido en .env.")
    return email


def get_or_create_default_user(session: Session) -> User:
    email = _default_user_email()
    existing_user = session.scalar(select(User).where(User.email == email))
    if existing_user:
        return existing_user

    user = User(
        email=email,
        password_hash=None,
        is_email_verified=True,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def resolve_owner_user(session: Session, owner_user: User | None = None) -> User:
    return owner_user if owner_user else get_or_create_default_user(session)


def upsert_product(
    session: Session,
    url: str,
    desired_price: Decimal,
    owner_user: User | None = None,
) -> Product:
    normalized_url = url.strip()
    if not normalized_url:
        raise ValueError("La URL no puede estar vacia.")

    store_code = detect_store(normalized_url)
    owner = resolve_owner_user(session, owner_user)

    existing = session.scalar(
        select(Product).where(Product.user_id == owner.id, Product.url == normalized_url)
    )
    if existing:
        try:
            existing.desired_price = desired_price
            existing.store = store_code
            existing.is_active = True
            session.commit()
            session.refresh(existing)
            return existing
        except Exception as exc:
            session.rollback()
            raise RuntimeError(f"No se pudo actualizar el producto existente: {exc}") from exc

    product = Product(
        user_id=owner.id,
        url=normalized_url,
        store=store_code,
        desired_price=desired_price,
        currency="EUR",
        last_status="never_checked",
    )
    try:
        session.add(product)
        session.commit()
        session.refresh(product)
        return product
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo guardar el producto: {exc}") from exc


def list_products(session: Session, owner_user: User | None = None) -> list[Product]:
    owner = resolve_owner_user(session, owner_user)
    query = select(Product).where(Product.user_id == owner.id).order_by(Product.created_at.desc())
    return list(session.scalars(query).all())


def get_product_history(
    session: Session,
    product_id: int,
    owner_user: User | None = None,
) -> list[PriceHistory]:
    owner = resolve_owner_user(session, owner_user)
    query = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id, PriceHistory.user_id == owner.id)
        .order_by(PriceHistory.checked_at.asc(), PriceHistory.id.asc())
    )
    return list(session.scalars(query).all())


def delete_product(
    session: Session,
    product_id: int,
    owner_user: User | None = None,
) -> bool:
    owner = resolve_owner_user(session, owner_user)
    product = session.scalar(select(Product).where(Product.id == product_id, Product.user_id == owner.id))
    if not product:
        return False

    try:
        session.delete(product)
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo eliminar el producto: {exc}") from exc

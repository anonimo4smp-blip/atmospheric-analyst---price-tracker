from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Alert, PriceHistory, Product
from app.scrapers import resolve_scraper
from app.services.alert_rules import next_below_state, should_create_alert
from app.services.auth_email_service import _send_smtp_email

settings = get_settings()


@dataclass
class PriceCheckSummary:
    total_products: int = 0
    checked_ok: int = 0
    checked_failed: int = 0
    alerts_created: int = 0


def _check_product(session: Session, product: Product, summary: PriceCheckSummary) -> None:
    summary.total_products += 1
    checked_at = datetime.now(timezone.utc)

    try:
        scraper = resolve_scraper(product.url)
        if not scraper:
            raise ValueError("Tienda no soportada para scraping.")

        result = scraper.fetch_price(product.url)
        product.title = result.title or product.title
        product.image_url = result.image_url or product.image_url
        product.currency = result.currency
        product.last_checked_at = checked_at

        if not result.in_stock or result.price is None:
            product.last_status = "unavailable"
            product.last_error = "Producto sin stock o precio no visible."
            product.was_below_desired = False
            session.add(
                PriceHistory(
                    user_id=product.user_id,
                    product_id=product.id,
                    title_snapshot=product.title,
                    price=None,
                    currency=product.currency,
                    status="unavailable",
                    error_message=product.last_error,
                    checked_at=checked_at,
                )
            )
            summary.checked_failed += 1
            return

        product.last_price = result.price
        product.last_status = "ok"
        product.last_error = None
        session.add(
            PriceHistory(
                user_id=product.user_id,
                product_id=product.id,
                title_snapshot=product.title,
                price=result.price,
                currency=result.currency,
                status="ok",
                error_message=None,
                checked_at=checked_at,
            )
        )

        if should_create_alert(
            was_below_desired=product.was_below_desired,
            current_price=result.price,
            desired_price=product.desired_price,
            in_stock=result.in_stock,
        ):
            recipient_email = (
                product.user.email
                if product.user and product.user.email and product.user.email.strip()
                else settings.alert_email
            )
            session.add(
                Alert(
                    user_id=product.user_id,
                    product_id=product.id,
                    email_to=recipient_email,
                    desired_price=product.desired_price,
                    triggered_price=result.price,
                    currency=result.currency,
                    status="pending",
                )
            )
            summary.alerts_created += 1

        product.was_below_desired = next_below_state(
            current_price=result.price,
            desired_price=product.desired_price,
            in_stock=result.in_stock,
        )
        summary.checked_ok += 1
    except Exception as exc:
        product.last_checked_at = checked_at
        product.last_status = "error"
        product.last_error = str(exc)
        product.was_below_desired = False
        session.add(
            PriceHistory(
                user_id=product.user_id,
                product_id=product.id,
                title_snapshot=product.title,
                price=None,
                currency=product.currency,
                status="error",
                error_message=str(exc),
                checked_at=checked_at,
            )
        )
        summary.checked_failed += 1


def _commit_or_raise(session: Session) -> None:
    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudieron persistir los resultados de scraping: {exc}") from exc


def run_price_check(session: Session) -> PriceCheckSummary:
    summary = PriceCheckSummary()
    products = list(session.scalars(select(Product).where(Product.is_active.is_(True))).all())
    for product in products:
        _check_product(session, product, summary)
    _commit_or_raise(session)
    return summary


def run_price_check_for_user(session: Session, user_id: int) -> PriceCheckSummary:
    summary = PriceCheckSummary()
    products = list(
        session.scalars(select(Product).where(Product.is_active.is_(True), Product.user_id == user_id)).all()
    )
    for product in products:
        _check_product(session, product, summary)
    _commit_or_raise(session)
    return summary


def run_price_check_for_product(session: Session, product_id: int) -> PriceCheckSummary:
    summary = PriceCheckSummary()
    product = session.get(Product, product_id)
    if not product or not product.is_active:
        return summary
    _check_product(session, product, summary)
    _commit_or_raise(session)
    return summary


def list_pending_alerts(session: Session) -> list[dict]:
    query = (
        select(Alert, Product)
        .join(Product, Product.id == Alert.product_id)
        .where(Alert.status == "pending")
        .order_by(Alert.triggered_at.asc(), Alert.id.asc())
    )
    rows = session.execute(query).all()
    return [
        {
            "id": alert.id,
            "product_id": product.id,
            "product_title": product.title,
            "product_url": product.url,
            "email_to": alert.email_to,
            "desired_price": alert.desired_price,
            "triggered_price": alert.triggered_price,
            "currency": alert.currency,
            "triggered_at": alert.triggered_at,
        }
        for alert, product in rows
    ]


def mark_alert_as_sent(session: Session, alert_id: int) -> None:
    alert = session.get(Alert, alert_id)
    if not alert:
        raise ValueError(f"No existe una alerta con id={alert_id}.")

    alert.status = "sent"
    alert.error_message = None
    alert.sent_at = datetime.now(timezone.utc)
    session.commit()


def send_alert_email(session: Session, alert_id: int) -> None:
    query = (
        select(Alert, Product)
        .join(Product, Product.id == Alert.product_id)
        .where(Alert.id == alert_id)
    )
    row = session.execute(query).first()
    if not row:
        raise ValueError(f"No existe una alerta con id={alert_id}.")

    alert, product = row
    title = product.title or product.url
    subject = f"Precio objetivo alcanzado: {title}"
    body = (
        f"Tu producto '{title}' ha bajado a {alert.triggered_price} {alert.currency} "
        f"(objetivo: {alert.desired_price} {alert.currency}).\n\n"
        f"URL: {product.url}"
    )
    _send_smtp_email(to_email=alert.email_to, subject=subject, body=body)

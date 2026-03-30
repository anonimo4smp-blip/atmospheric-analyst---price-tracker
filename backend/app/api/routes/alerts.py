from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.api.deps import AppOwnerUser
from app.db.session import get_db_session
from app.db.models import Alert, Product
from app.schemas.alert import AlertResponse

router = APIRouter()


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> list[AlertResponse]:
    rows = db.execute(
        select(Alert, Product)
        .join(Product, Product.id == Alert.product_id)
        .where(Alert.user_id == owner_user.id)
        .order_by(Alert.triggered_at.desc())
        .limit(200)
    ).all()

    return [
        AlertResponse(
            id=alert.id,
            product_id=alert.product_id,
            product_title=product.title,
            product_url=product.url,
            desired_price=float(alert.desired_price),
            triggered_price=float(alert.triggered_price),
            currency=alert.currency,
            status=alert.status,
            error_message=alert.error_message,
            triggered_at=alert.triggered_at,
            sent_at=alert.sent_at,
        )
        for alert, product in rows
    ]

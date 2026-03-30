from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer


class PendingAlertResponse(BaseModel):
    id: int
    product_id: int
    product_title: str | None
    product_url: str
    email_to: str
    desired_price: Decimal
    triggered_price: Decimal
    currency: str
    triggered_at: datetime

    @field_serializer("desired_price", "triggered_price")
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)


class AlertResponse(BaseModel):
    id: int
    product_id: int
    product_title: str | None
    product_url: str
    desired_price: float
    triggered_price: float
    currency: str
    status: str
    error_message: str | None
    triggered_at: datetime
    sent_at: datetime | None

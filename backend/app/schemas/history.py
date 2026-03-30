from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class PriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    title_snapshot: str | None
    price: Decimal | None
    currency: str
    status: str
    error_message: str | None
    checked_at: datetime

    @field_serializer("price")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

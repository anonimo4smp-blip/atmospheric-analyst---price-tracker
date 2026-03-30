from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ProductUpsertRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    desired_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    store: str
    title: str | None
    image_url: str | None
    desired_price: Decimal
    last_price: Decimal | None
    currency: str
    last_status: str
    last_error: str | None
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("desired_price", "last_price")
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

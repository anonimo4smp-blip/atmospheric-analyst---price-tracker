from pydantic import BaseModel


class PriceCheckSummaryResponse(BaseModel):
    total_products: int
    checked_ok: int
    checked_failed: int
    alerts_created: int

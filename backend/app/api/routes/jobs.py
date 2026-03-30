from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AppOwnerUser
from app.db.session import get_db_session
from app.schemas.job import PriceCheckSummaryResponse
from app.services.price_check_service import run_price_check_for_user

router = APIRouter()


@router.post("/jobs/check-now", response_model=PriceCheckSummaryResponse)
def check_now(
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> PriceCheckSummaryResponse:
    try:
        summary = run_price_check_for_user(db, owner_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return PriceCheckSummaryResponse(
        total_products=summary.total_products,
        checked_ok=summary.checked_ok,
        checked_failed=summary.checked_failed,
        alerts_created=summary.alerts_created,
    )

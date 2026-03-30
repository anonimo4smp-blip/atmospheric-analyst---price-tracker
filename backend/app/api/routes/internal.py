from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_internal_api_key
from app.db.session import get_db_session
from app.schemas.alert import PendingAlertResponse
from app.schemas.job import PriceCheckSummaryResponse
from app.services.price_check_service import list_pending_alerts, mark_alert_as_sent, run_price_check, send_alert_email

router = APIRouter(dependencies=[Depends(require_internal_api_key)])


@router.post("/jobs/check-prices", response_model=PriceCheckSummaryResponse)
def internal_check_prices(db: Session = Depends(get_db_session)) -> PriceCheckSummaryResponse:
    try:
        summary = run_price_check(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return PriceCheckSummaryResponse(
        total_products=summary.total_products,
        checked_ok=summary.checked_ok,
        checked_failed=summary.checked_failed,
        alerts_created=summary.alerts_created,
    )


@router.get("/alerts/pending", response_model=list[PendingAlertResponse])
def internal_pending_alerts(db: Session = Depends(get_db_session)) -> list[PendingAlertResponse]:
    pending = list_pending_alerts(db)
    return [PendingAlertResponse.model_validate(item) for item in pending]


@router.post("/alerts/{alert_id}/send-email")
def internal_send_alert_email(alert_id: int, db: Session = Depends(get_db_session)) -> dict[str, str]:
    try:
        send_alert_email(db, alert_id)
        mark_alert_as_sent(db, alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"status": "sent"}


@router.post("/alerts/{alert_id}/mark-sent")
def internal_mark_alert_sent(alert_id: int, db: Session = Depends(get_db_session)) -> dict[str, str]:
    try:
        mark_alert_as_sent(db, alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"status": "sent"}

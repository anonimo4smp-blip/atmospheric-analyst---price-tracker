from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AppOwnerUser
from app.db.session import get_db_session
from app.db.models import PriceHistory, Product as ProductModel
from app.schemas.history import PriceHistoryResponse
from app.schemas.product import ProductResponse, ProductUpsertRequest
from app.schemas.job import PriceCheckSummaryResponse
from app.services.product_service import delete_product, get_product_history, list_products, upsert_product
from app.services.price_check_service import run_price_check_for_product

router = APIRouter()


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_product(
    payload: ProductUpsertRequest,
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> ProductResponse:
    try:
        product = upsert_product(db, payload.url, payload.desired_price, owner_user=owner_user)
        run_price_check_for_product(db, product.id)
        db.refresh(product)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return ProductResponse.model_validate(product)


@router.get("/products", response_model=list[ProductResponse])
def get_products(
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> list[ProductResponse]:
    products = list_products(db, owner_user=owner_user)
    if not products:
        return []

    product_ids = [p.id for p in products]

    # Subconsulta: numera las entradas de historial por producto de más reciente a más antigua
    rn_col = func.row_number().over(
        partition_by=PriceHistory.product_id,
        order_by=[PriceHistory.checked_at.desc(), PriceHistory.id.desc()],
    ).label("rn")
    subq = (
        select(PriceHistory.product_id, PriceHistory.price, rn_col)
        .where(PriceHistory.product_id.in_(product_ids), PriceHistory.price.isnot(None))
        .subquery()
    )
    prev_rows = db.execute(
        select(subq.c.product_id, subq.c.price).where(subq.c.rn == 2)
    ).all()
    prev_price_map: dict[int, float] = {row.product_id: float(row.price) for row in prev_rows}

    result = []
    for product in products:
        resp = ProductResponse.model_validate(product)
        resp.previous_price = prev_price_map.get(product.id)
        result.append(resp)
    return result


@router.get("/products/{product_id}/history", response_model=list[PriceHistoryResponse])
def get_history(
    product_id: int,
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> list[PriceHistoryResponse]:
    history = get_product_history(db, product_id, owner_user=owner_user)
    return [PriceHistoryResponse.model_validate(point) for point in history]


@router.post("/products/{product_id}/check", response_model=PriceCheckSummaryResponse)
def check_product_now(
    product_id: int,
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> PriceCheckSummaryResponse:
    product = db.get(ProductModel, product_id)
    if not product or product.user_id != owner_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")
    try:
        summary = run_price_check_for_product(db, product_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return PriceCheckSummaryResponse(
        total_products=summary.total_products,
        checked_ok=summary.checked_ok,
        checked_failed=summary.checked_failed,
        alerts_created=summary.alerts_created,
    )


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product(
    product_id: int,
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> None:
    try:
        was_deleted = delete_product(db, product_id, owner_user=owner_user)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if not was_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")

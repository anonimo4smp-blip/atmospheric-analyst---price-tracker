from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AppOwnerUser
from app.db.session import get_db_session
from app.schemas.history import PriceHistoryResponse
from app.schemas.product import ProductResponse, ProductUpsertRequest
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
    return [ProductResponse.model_validate(product) for product in products]


@router.get("/products/{product_id}/history", response_model=list[PriceHistoryResponse])
def get_history(
    product_id: int,
    owner_user: AppOwnerUser,
    db: Session = Depends(get_db_session),
) -> list[PriceHistoryResponse]:
    history = get_product_history(db, product_id, owner_user=owner_user)
    return [PriceHistoryResponse.model_validate(point) for point in history]


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

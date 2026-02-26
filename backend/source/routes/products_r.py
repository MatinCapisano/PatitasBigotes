from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from source.dependencies.auth_d import require_admin
from source.db.session import get_db
from source.errors import raise_http_error_from_exception
from source.schemas import (
    CreateProductRequest,
    PatchProductRequest,
    UpdateProductRequest,
)
from source.services.products_s import (
    create_product as create_product_s,
    delete_product_hard,
    filter_and_sort_products,
    get_product_by_id,
    update_product as update_product_s,
)

router = APIRouter()


@router.get("/products")
def get_products(
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: Optional[Literal["price", "name"]] = Query(None),
    sort_order: Literal["asc", "desc"] = Query("asc"),
    _db: Session = Depends(get_db),
):
    products = filter_and_sort_products(
        min_price=min_price,
        max_price=max_price,
        category=category,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return {
        "data": products,
        "meta": {
            "filters": {
                "min_price": min_price,
                "max_price": max_price,
                "category": category,
                "sort_by": sort_by,
                "sort_order": sort_order,
            }
        },
    }


@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    _db: Session = Depends(get_db),
):
    product = get_product_by_id(product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return {"data": product}


@router.post("/products")
def create_product(
    payload: CreateProductRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        product = create_product_s(payload=payload.model_dump(), db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": product}


@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    payload: UpdateProductRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        product = update_product_s(
            product_id=product_id,
            updates=payload.model_dump(),
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"data": product}


@router.patch("/products/{product_id}")
def patch_product(
    product_id: int,
    payload: PatchProductRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="at least one field is required")
    try:
        product = update_product_s(
            product_id=product_id,
            updates=updates,
            db=db,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"data": product}


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        product = delete_product_hard(product_id=product_id, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"data": product}

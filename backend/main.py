from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.security import decode_access_token
from source.services.products_s import filter_and_sort_products, get_product_by_id

app = FastAPI(
    title="Sales API",
    version="0.1.0",
    description="API para página de ventas. Etapa inicial."
)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject",
        )

    return payload


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required",
        )

    return current_user


@app.get("/health")
def health_check():
    return {"status": "ok"}


# -------------------------
# PRODUCTS
# -------------------------

PRODUCTS = [
    {"id": 1, "name": "Laptop", "price": 1200, "category": "electronics"},
    {"id": 2, "name": "Mouse", "price": 25, "category": "electronics"},
    {"id": 3, "name": "Chair", "price": 80, "category": "furniture"},
]

@app.get("/products")
def get_products(
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    category: Optional[str] = Query(None),
    sort_by: Optional[Literal["price", "name"]] = Query(None),
    sort_order: Literal["asc", "desc"] = Query("asc"),
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
        }
    }

@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = get_product_by_id(product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "data": product
    }


@app.post("/products")
def create_product(_: dict = Depends(require_admin)):
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }


@app.put("/products/{product_id}")
def update_product(product_id: int, _: dict = Depends(require_admin)):
    return {
        "data": {
            "id": product_id,
            "status": "updated"
        }
    }


@app.delete("/products/{product_id}")
def delete_product(product_id: int, _: dict = Depends(require_admin)):
    return {
        "data": {
            "id": product_id,
            "status": "deleted"
        }
    }


# -------------------------
# USERS
# -------------------------

@app.post("/users")
def create_user():
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }


# -------------------------
# ORDERS
# -------------------------

@app.post("/orders")
def create_order(_: dict = Depends(get_current_user)):
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }


# -------------------------
# TURNS
# -------------------------

@app.post("/turns")
def create_turn(_: dict = Depends(get_current_user)):
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }

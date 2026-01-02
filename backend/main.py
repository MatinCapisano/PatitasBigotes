from fastapi import FastAPI,Query
from source.services.products_s import filter_and_sort_products
from  typing import Optional,Literal

app = FastAPI(
    title="Sales API",
    version="0.1.0",
    description="API para página de ventas. Etapa inicial."
)


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
    return {
        "data": {
            "id": product_id,
            "name": "placeholder product",
            "price": 0
        }
    }


@app.post("/products")
def create_product():
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }


@app.put("/products/{product_id}")
def update_product(product_id: int):
    return {
        "data": {
            "id": product_id,
            "status": "updated"
        }
    }


@app.delete("/products/{product_id}")
def delete_product(product_id: int):
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
def create_order():
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
def create_turn():
    return {
        "data": {
            "id": 1,
            "status": "created"
        }
    }

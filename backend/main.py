from fastapi import FastAPI

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

@app.get("/products")
def list_products():
    return {
        "data": [],
        "meta": {
            "pagination": {
                "page": 1,
                "limit": 20,
                "total": 0
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

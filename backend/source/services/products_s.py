from typing import Literal, Optional

# Datos de prueba (persistencia temporal)
PRODUCTS = [
    {
        "id": 1,
        "name": "Laptop",
        "price": 1200,
        "category": "electronics",
        "active": 1,
        "stock": 10,
    },
    {
        "id": 2,
        "name": "Mouse",
        "price": 25,
        "category": "electronics",
        "active": 1,
        "stock": 50,
    },
    {
        "id": 3,
        "name": "Chair",
        "price": 80,
        "category": "furniture",
        "active": 1,
        "stock": 20,
    },
]


def filter_and_sort_products(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    sort_by: Optional[Literal["price", "name"]] = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> list[dict]:
    # 1. Partimos solo de productos activos
    result = [p for p in PRODUCTS if p.get("active") == 1]

    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]

    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    if category is not None:
        result = [p for p in result if p["category"] == category]

    if sort_by is not None:
        reverse = sort_order == "desc"
        result = sorted(result, key=lambda p: p[sort_by], reverse=reverse)

    return result


def update_product(product_id: int, updates: dict) -> dict | None:
    """
    Actualiza los campos permitidos de un producto.
    Devuelve el producto actualizado o None si no existe.
    """

    # Campos que el admin puede modificar
    allowed_fields = {
        "name",
        "description",
        "price",
        "category",
        "active",
        "stock",
    }

    for product in PRODUCTS:
        if product["id"] == product_id:
            for field, value in updates.items():
                if field in allowed_fields:
                    product[field] = value

            return product

    return None


def get_product_by_id(product_id: int) -> Optional[dict]:
    for product in PRODUCTS:
        if product["id"] == product_id:
            return product
    return None


def add_stock(product_id: int, quantity: int) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    product = get_product_by_id(product_id)
    if product is None:
        raise LookupError("product not found")

    current_stock = int(product.get("stock", 0))
    product["stock"] = current_stock + quantity
    return product


def decrement_stock(product_id: int, quantity: int) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    product = get_product_by_id(product_id)
    if product is None:
        raise LookupError("product not found")

    current_stock = int(product.get("stock", 0))
    if current_stock < quantity:
        raise ValueError("insufficient stock")

    product["stock"] = current_stock - quantity
    return product


def deactivate_product(product_id: int) -> dict | None:
    for product in PRODUCTS:
        if product["id"] == product_id:
            product["active"] = 0
            return product

    return None


def activate_product(product_id: int) -> dict | None:
    for product in PRODUCTS:
        if product["id"] == product_id:
            product["active"] = 1
            return product

    return None

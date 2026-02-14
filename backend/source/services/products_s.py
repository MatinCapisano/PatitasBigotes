from typing import Literal, Optional

# Datos de prueba (persistencia temporal)
PRODUCTS = [
    {
        "id": 1,
        "name": "Laptop",
        "price": 1200,
        "category": "electronics",
        "active": 1,
    },
    {
        "id": 2,
        "name": "Mouse",
        "price": 25,
        "category": "electronics",
        "active": 1,
    },
    {
        "id": 3,
        "name": "Chair",
        "price": 80,
        "category": "furniture",
        "active": 1,
    },
]

PRODUCT_VARIANTS = [
    {
        "id": 101,
        "product_id": 1,
        "sku": "LAPTOP-13-GRAY",
        "size": '13"',
        "color": "gray",
        "price": 1200,
        "stock": 6,
        "active": 1,
    },
    {
        "id": 102,
        "product_id": 1,
        "sku": "LAPTOP-15-BLACK",
        "size": '15"',
        "color": "black",
        "price": 1400,
        "stock": 4,
        "active": 1,
    },
    {
        "id": 201,
        "product_id": 2,
        "sku": "MOUSE-STD-BLACK",
        "size": "std",
        "color": "black",
        "price": 25,
        "stock": 50,
        "active": 1,
    },
    {
        "id": 301,
        "product_id": 3,
        "sku": "CHAIR-M-BLUE",
        "size": "M",
        "color": "blue",
        "price": 80,
        "stock": 12,
        "active": 1,
    },
    {
        "id": 302,
        "product_id": 3,
        "sku": "CHAIR-L-BLUE",
        "size": "L",
        "color": "blue",
        "price": 85,
        "stock": 8,
        "active": 1,
    },
]

_next_variant_id = max((variant["id"] for variant in PRODUCT_VARIANTS), default=0) + 1


def _ensure_default_variant_for_product(product: dict) -> dict:
    global _next_variant_id

    for variant in PRODUCT_VARIANTS:
        if variant["product_id"] == product["id"] and variant.get("active") == 1:
            return variant

    default_variant = {
        "id": _next_variant_id,
        "product_id": product["id"],
        "sku": f"PRODUCT-{product['id']}-DEFAULT",
        "size": None,
        "color": None,
        "price": float(product["price"]),
        "stock": int(product.get("stock", 0)),
        "active": 1,
    }
    _next_variant_id += 1
    PRODUCT_VARIANTS.append(default_variant)
    return default_variant


def ensure_product_has_variant(product_id: int) -> list[dict]:
    product = get_product_by_id(product_id)
    if product is None:
        raise LookupError("product not found")
    if product.get("active") != 1:
        raise ValueError("inactive products cannot create variants")

    variants = [
        variant
        for variant in PRODUCT_VARIANTS
        if variant["product_id"] == product_id and variant.get("active") == 1
    ]
    if variants:
        return variants

    return [_ensure_default_variant_for_product(product)]


def _recalculate_product_stock(product_id: int) -> None:
    total_stock = sum(
        int(variant.get("stock", 0))
        for variant in PRODUCT_VARIANTS
        if variant["product_id"] == product_id and variant.get("active") == 1
    )
    product = get_product_by_id(product_id)
    if product is not None:
        product["stock"] = total_stock


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

    variants = ensure_product_has_variant(product_id)
    if not variants:
        raise ValueError("product has no active variants")

    # Compatibilidad: agrega stock en la primera variante activa.
    add_variant_stock(variants[0]["id"], quantity)
    _recalculate_product_stock(product_id)
    return product


def decrement_stock(product_id: int, quantity: int) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    product = get_product_by_id(product_id)
    if product is None:
        raise LookupError("product not found")

    remaining = quantity
    variants = ensure_product_has_variant(product_id)
    total_stock = sum(int(variant.get("stock", 0)) for variant in variants)
    if total_stock < quantity:
        raise ValueError("insufficient stock")

    for variant in variants:
        if remaining == 0:
            break
        current = int(variant.get("stock", 0))
        if current == 0:
            continue
        taken = min(current, remaining)
        variant["stock"] = current - taken
        remaining -= taken

    _recalculate_product_stock(product_id)
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


def get_variant_by_id(variant_id: int) -> Optional[dict]:
    for variant in PRODUCT_VARIANTS:
        if variant["id"] != variant_id or variant.get("active") != 1:
            continue

        product = get_product_by_id(variant["product_id"])
        if product is None or product.get("active") != 1:
            return None

        return variant
    return None


def list_variants_by_product_id(product_id: int) -> list[dict]:
    return [
        variant
        for variant in PRODUCT_VARIANTS
        if variant["product_id"] == product_id and variant.get("active") == 1
    ]


def add_variant_stock(variant_id: int, quantity: int) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    variant = get_variant_by_id(variant_id)
    if variant is None:
        raise LookupError("variant not found")

    current_stock = int(variant.get("stock", 0))
    variant["stock"] = current_stock + quantity
    _recalculate_product_stock(variant["product_id"])
    return variant


def decrement_variant_stock(variant_id: int, quantity: int) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    variant = get_variant_by_id(variant_id)
    if variant is None:
        raise LookupError("variant not found")

    current_stock = int(variant.get("stock", 0))
    if current_stock < quantity:
        raise ValueError("insufficient stock")

    variant["stock"] = current_stock - quantity
    _recalculate_product_stock(variant["product_id"])
    return variant


for _product in PRODUCTS:
    ensure_product_has_variant(_product["id"])
    _recalculate_product_stock(_product["id"])

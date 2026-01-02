from typing import List, Optional, Literal


from typing import List, Optional, Literal

# Datos de prueba (persistencia temporal)
PRODUCTS = [
    {"id": 1, "name": "Laptop", "price": 1200, "category": "electronics"},
    {"id": 2, "name": "Mouse", "price": 25, "category": "electronics"},
    {"id": 3, "name": "Chair", "price": 80, "category": "furniture"},
]


def filter_and_sort_products(
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    sort_by: Optional[Literal["price", "name"]] = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> List[dict]:
    result = PRODUCTS

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

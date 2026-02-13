from __future__ import annotations

from datetime import datetime
from typing import Iterable


# Core (pure logic)
def is_discount_currently_valid(discount: dict, at: datetime | None = None) -> bool:
    now = at or datetime.utcnow()
    if not discount.get("is_active", False):
        return False

    starts_at = discount.get("starts_at")
    ends_at = discount.get("ends_at")

    if starts_at is not None and now < starts_at:
        return False
    if ends_at is not None and now > ends_at:
        return False
    return True


def select_best_discount(discounts: Iterable[dict], unit_price: float) -> dict | None:
    best: dict | None = None
    best_amount = 0.0

    for discount in discounts:
        amount = calculate_line_discount(unit_price=unit_price, discount=discount)
        if amount > best_amount:
            best = discount
            best_amount = amount

    return best


def calculate_line_discount(unit_price: float, discount: dict) -> float:
    discount_type = discount.get("type")
    value = float(discount.get("value", 0))

    if unit_price <= 0 or value <= 0:
        return 0.0

    if discount_type == "percent":
        amount = unit_price * (value / 100.0)
    elif discount_type == "fixed":
        amount = value
    else:
        return 0.0

    return max(0.0, min(amount, unit_price))


def calculate_line_pricing(unit_price: float, quantity: int, discount: dict | None) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    discount_amount = 0.0
    discount_id = None
    if discount is not None:
        discount_amount = calculate_line_discount(unit_price=unit_price, discount=discount)
        discount_id = discount.get("id")

    final_unit_price = max(0.0, unit_price - discount_amount)

    return {
        "unit_price": float(unit_price),
        "quantity": quantity,
        "discount_id": discount_id,
        "discount_amount": float(discount_amount),
        "final_unit_price": float(final_unit_price),
        "line_total": float(final_unit_price * quantity),
    }


# Query/repository-facing (stubs)
def get_applicable_discounts_for_product(product: dict, discounts: Iterable[dict]) -> list[dict]:
    applicable: list[dict] = []
    product_id = product.get("id")
    category = product.get("category")

    for discount in discounts:
        if not is_discount_currently_valid(discount):
            continue

        scope = discount.get("scope")
        scope_value = discount.get("scope_value")

        if scope == "all":
            applicable.append(discount)
        elif scope == "category" and str(scope_value) == str(category):
            applicable.append(discount)
        elif scope == "product" and str(scope_value) == str(product_id):
            applicable.append(discount)
        elif scope == "product_list":
            product_ids = discount.get("product_ids", [])
            if str(product_id) in {str(pid) for pid in product_ids}:
                applicable.append(discount)

    return applicable


def set_discount_product_list(discount: dict, product_ids: list[int]) -> dict:
    discount["product_ids"] = list(dict.fromkeys(product_ids))
    return discount


def add_products_to_discount(discount: dict, product_ids: list[int]) -> dict:
    current = set(discount.get("product_ids", []))
    current.update(product_ids)
    discount["product_ids"] = sorted(current)
    return discount


def remove_products_from_discount(discount: dict, product_ids: list[int]) -> dict:
    to_remove = set(product_ids)
    current = [pid for pid in discount.get("product_ids", []) if pid not in to_remove]
    discount["product_ids"] = current
    return discount


# Order orchestration helpers
def reprice_order_items(order: dict, discounts: Iterable[dict], products_by_id: dict[int, dict]) -> dict:
    for item in order.get("items", []):
        product = products_by_id.get(item["product_id"])
        if product is None:
            continue

        applicable = get_applicable_discounts_for_product(product=product, discounts=discounts)
        best = select_best_discount(applicable, unit_price=float(item["unit_price"]))
        pricing = calculate_line_pricing(
            unit_price=float(item["unit_price"]),
            quantity=int(item["quantity"]),
            discount=best,
        )

        item["discount_id"] = pricing["discount_id"]
        item["discount_amount"] = pricing["discount_amount"]
        item["final_unit_price"] = pricing["final_unit_price"]
        item["line_total"] = pricing["line_total"]

    return recalculate_order_totals(order)


def recalculate_order_totals(order: dict) -> dict:
    subtotal = 0.0
    discount_total = 0.0
    total_amount = 0.0

    for item in order.get("items", []):
        unit_price = float(item.get("unit_price", 0))
        qty = int(item.get("quantity", 0))
        line_total = float(item.get("line_total", unit_price * qty))
        line_discount = float(item.get("discount_amount", 0)) * qty

        subtotal += unit_price * qty
        discount_total += line_discount
        total_amount += line_total

    order["subtotal"] = float(subtotal)
    order["discount_total"] = float(discount_total)
    order["total_amount"] = float(total_amount)
    return order


def freeze_order_pricing(order: dict) -> dict:
    order["pricing_frozen"] = True
    order["pricing_frozen_at"] = datetime.utcnow().isoformat() + "Z"
    return order


def validate_order_pricing_before_submit(order: dict) -> None:
    if not order.get("items"):
        raise ValueError("cannot submit an empty order")
    if float(order.get("total_amount", 0)) < 0:
        raise ValueError("order total cannot be negative")

from __future__ import annotations

from datetime import datetime

from source.services.discount_s import (
    freeze_order_pricing,
    reprice_order_items,
    validate_order_pricing_before_submit,
)
from source.services.products_s import get_product_by_id, decrement_stock

ALLOWED_ORDER_STATUS = {"draft", "submitted", "paid", "cancelled"}

_orders: list[dict] = []
_discounts: list[dict] = []
_next_order_id = 1
_next_item_id = 1


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _recalculate_order_total(order: dict) -> None:
    products_by_id: dict[int, dict] = {}
    for item in order["items"]:
        product = get_product_by_id(item["product_id"])
        if product is not None:
            products_by_id[item["product_id"]] = product

    reprice_order_items(
        order=order,
        discounts=_discounts,
        products_by_id=products_by_id,
    )
    order["updated_at"] = _utc_now_iso()


def _build_order(user_ref: str) -> dict:
    global _next_order_id
    now = _utc_now_iso()
    order = {
        "id": _next_order_id,
        "user_ref": user_ref,
        "status": "draft",
        "items": [],
        "subtotal": 0.0,
        "discount_total": 0.0,
        "total_amount": 0.0,
        "pricing_frozen": False,
        "pricing_frozen_at": None,
        "created_at": now,
        "updated_at": now,
    }
    _next_order_id += 1
    return order


def _find_user_draft_order(user_ref: str) -> dict | None:
    for order in _orders:
        if order["user_ref"] == user_ref and order["status"] == "draft":
            return order
    return None


def get_or_create_draft_order(user_ref: str) -> tuple[dict, bool]:
    draft = _find_user_draft_order(user_ref)
    if draft is not None:
        return draft, False

    created = _build_order(user_ref)
    _orders.append(created)
    return created, True


def get_order_for_user(user_ref: str, order_id: int) -> dict | None:
    for order in _orders:
        if order["id"] == order_id and order["user_ref"] == user_ref:
            return order
    return None


def add_item_to_draft_order(
    user_ref: str,
    product: dict,
    quantity: int,
) -> dict:
    global _next_item_id

    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    order, _ = get_or_create_draft_order(user_ref)
    if order["status"] != "draft":
        raise ValueError("items can only be edited in draft status")

    for item in order["items"]:
        if item["product_id"] == product["id"]:
            item["quantity"] += quantity
            _recalculate_order_total(order)
            return order

    order["items"].append(
        {
            "id": _next_item_id,
            "product_id": product["id"],
            "product_name": product.get("name"),
            "quantity": quantity,
            "unit_price": float(product["price"]),
        }
    )
    _next_item_id += 1
    _recalculate_order_total(order)
    return order


def remove_item_from_draft_order(user_ref: str, item_id: int) -> dict | None:
    order = _find_user_draft_order(user_ref)
    if order is None:
        return None

    if order["status"] != "draft":
        raise ValueError("items can only be edited in draft status")

    for idx, item in enumerate(order["items"]):
        if item["id"] == item_id:
            del order["items"][idx]
            _recalculate_order_total(order)
            return order

    return None


def change_order_status(
    user_ref: str,
    order_id: int,
    new_status: str,
) -> dict:
    if new_status not in ALLOWED_ORDER_STATUS:
        raise ValueError("invalid status")

    order = get_order_for_user(user_ref, order_id)
    if order is None:
        raise LookupError("order not found")

    if order["status"] == new_status:
        return order

    if order["status"] == "draft" and new_status != "draft" and not order["items"]:
        raise ValueError("cannot leave draft with an empty order")

    if order["status"] != "draft" and new_status == "draft":
        raise ValueError("cannot move non-draft order back to draft")

    if order["status"] == "draft" and new_status == "submitted":
        _recalculate_order_total(order)
        validate_order_pricing_before_submit(order)
        freeze_order_pricing(order)

    order["status"] = new_status
    order["updated_at"] = _utc_now_iso()
    return order


def pay_order(
    user_ref: str,
    order_id: int,
    payment_ref: str,
    paid_amount: float,
) -> dict:
    if not payment_ref or not payment_ref.strip():
        raise ValueError("payment_ref is required")
    if paid_amount <= 0:
        raise ValueError("paid_amount must be greater than 0")

    order = get_order_for_user(user_ref=user_ref, order_id=order_id)
    if order is None:
        raise LookupError("order not found")

    if order["status"] != "submitted" and order["status"] != "paid":
        raise ValueError("order can only be paid from submitted status")

    if not order["items"]:
        raise ValueError("cannot pay an empty order")

    if order["status"] == "cancelled":
        raise ValueError("cannot pay a cancelled order")

    expected_total = round(float(order.get("total_amount", 0.0)), 2)
    received_total = round(float(paid_amount), 2)
    if expected_total != received_total:
        raise ValueError("paid_amount does not match order total")

    existing_ref = order.get("payment_ref")
    if order["status"] == "paid":
        if existing_ref == payment_ref:
            return order
        raise ValueError("order already paid with a different payment_ref")

    # Pre-validacion para evitar descuentos parciales por falta de stock.
    for item in order["items"]:
        product = get_product_by_id(item["product_id"])
        if product is None:
            raise ValueError(f"product {item['product_id']} not found")

        current_stock = int(product.get("stock", 0))
        if current_stock < item["quantity"]:
            raise ValueError(
                f"insufficient stock for product {item['product_id']}"
            )

    # Solo si toda la orden tiene stock, descontamos.
    for item in order["items"]:
        decrement_stock(item["product_id"], item["quantity"])

    now = _utc_now_iso()
    order["status"] = "paid"
    order["payment_ref"] = payment_ref
    order["paid_amount"] = received_total
    order["paid_at"] = now
    order["updated_at"] = now
    return order

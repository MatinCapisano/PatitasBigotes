from __future__ import annotations

from datetime import datetime

ALLOWED_ORDER_STATUS = {"draft", "submitted", "paid", "cancelled"}

_orders: list[dict] = []
_next_order_id = 1
_next_item_id = 1


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _recalculate_order_total(order: dict) -> None:
    order["total_amount"] = sum(
        item["quantity"] * item["unit_price"]
        for item in order["items"]
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
        "total_amount": 0.0,
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

    if order["status"] != "draft" and new_status == "draft":
        raise ValueError("cannot move non-draft order back to draft")

    order["status"] = new_status
    order["updated_at"] = _utc_now_iso()
    return order

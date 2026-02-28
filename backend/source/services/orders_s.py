from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from source.db.models import Order, OrderItem, ProductVariant
from source.services.discount_s import (
    list_discounts,
    reprice_order_items,
    validate_order_pricing_before_submit,
)
from source.services.payment_s import confirm_manual_payment_for_order
from source.services.products_s import get_product_by_id
from source.services.users_s import get_or_create_user_by_contact, serialize_user_basic

ALLOWED_ORDER_STATUS = {"draft", "submitted", "paid", "cancelled"}


def _utc_now() -> datetime:
    return datetime.utcnow()


def _order_query(db: Session):
    return db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.variant),
        joinedload(Order.items).joinedload(OrderItem.product),
    )


def _variant_label(variant: ProductVariant | None) -> str:
    if variant is None:
        return "-/-"
    return f"{variant.size or '-'}/{variant.color or '-'}"


def _order_to_dict(order: Order) -> dict:
    items = []
    for item in sorted(order.items, key=lambda x: x.id):
        items.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "product_name": item.product.name if item.product is not None else None,
                "variant_label": _variant_label(item.variant),
                "quantity": int(item.quantity),
                "unit_price": float(item.unit_price),
                "discount_id": item.discount_id,
                "discount_amount": float(item.discount_amount or 0),
                "final_unit_price": float(item.final_unit_price or 0),
                "line_total": float(item.line_total or 0),
            }
        )

    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "currency": order.currency,
        "items": items,
        "subtotal": float(order.subtotal or 0),
        "discount_total": float(order.discount_total or 0),
        "total_amount": float(order.total_amount or 0),
        "pricing_frozen": bool(order.pricing_frozen),
        "pricing_frozen_at": order.pricing_frozen_at,
        "submitted_at": order.submitted_at,
        "paid_at": order.paid_at,
        "cancelled_at": order.cancelled_at,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def _recalculate_order_total(order: Order, db: Session, *, force: bool = False) -> None:
    if bool(order.pricing_frozen) and not force:
        raise ValueError("cannot recalculate a frozen order")

    order_payload = {
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "quantity": int(item.quantity),
                "unit_price": float(item.unit_price),
                "discount_id": item.discount_id,
                "discount_amount": float(item.discount_amount or 0),
                "final_unit_price": float(item.final_unit_price or 0),
                "line_total": float(item.line_total or 0),
            }
            for item in order.items
        ],
        "subtotal": float(order.subtotal or 0),
        "discount_total": float(order.discount_total or 0),
        "total_amount": float(order.total_amount or 0),
        "pricing_frozen": bool(order.pricing_frozen),
    }

    products_by_id: dict[int, dict] = {}
    for item in order_payload["items"]:
        product = get_product_by_id(item["product_id"], db=db)
        if product is not None:
            products_by_id[item["product_id"]] = product

    reprice_order_items(
        order=order_payload,
        discounts=list_discounts(db=db),
        products_by_id=products_by_id,
    )

    item_by_id = {item.id: item for item in order.items}
    for item_payload in order_payload["items"]:
        item = item_by_id.get(int(item_payload["id"]))
        if item is None:
            continue
        item.discount_id = item_payload.get("discount_id")
        item.discount_amount = float(item_payload.get("discount_amount", 0))
        item.final_unit_price = float(item_payload.get("final_unit_price", 0))
        item.line_total = float(item_payload.get("line_total", 0))

    order.subtotal = float(order_payload.get("subtotal", 0))
    order.discount_total = float(order_payload.get("discount_total", 0))
    order.total_amount = float(order_payload.get("total_amount", 0))


def get_or_create_draft_order(user_id: int, db: Session) -> tuple[dict, bool]:
    draft = (
        _order_query(db)
        .filter(
            Order.user_id == user_id,
            Order.status == "draft",
        )
        .order_by(Order.created_at.desc(), Order.id.desc())
        .first()
    )
    if draft is not None:
        return _order_to_dict(draft), False

    created = Order(
        user_id=user_id,
        status="draft",
        currency="ARS",
        subtotal=0.0,
        discount_total=0.0,
        total_amount=0.0,
        pricing_frozen=False,
    )
    db.add(created)
    db.flush()
    db.refresh(created)
    return _order_to_dict(created), True


def _get_or_create_draft_order_model(user_id: int, db: Session) -> tuple[Order, bool]:
    draft = (
        _order_query(db)
        .filter(
            Order.user_id == user_id,
            Order.status == "draft",
        )
        .order_by(Order.created_at.desc(), Order.id.desc())
        .with_for_update()
        .first()
    )
    if draft is not None:
        return draft, False

    draft = Order(
        user_id=user_id,
        status="draft",
        currency="ARS",
        subtotal=0.0,
        discount_total=0.0,
        total_amount=0.0,
        pricing_frozen=False,
    )
    db.add(draft)
    db.flush()
    db.refresh(draft)
    return draft, True


def get_order_for_user(user_id: int, order_id: int, db: Session) -> dict | None:
    order = (
        _order_query(db)
        .filter(
            Order.id == order_id,
            Order.user_id == user_id,
        )
        .first()
    )
    if order is None:
        return None
    return _order_to_dict(order)


def add_item_to_draft_order(
    user_id: int,
    variant_id: int,
    quantity: int,
    db: Session,
) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    variant = (
        db.query(ProductVariant)
        .options(joinedload(ProductVariant.product))
        .filter(
            ProductVariant.id == variant_id,
            ProductVariant.is_active.is_(True),
        )
        .first()
    )
    if variant is None:
        raise ValueError("variant not found")

    order, _ = _get_or_create_draft_order_model(user_id=user_id, db=db)
    if order.status != "draft":
        raise ValueError("items can only be edited in draft status")

    existing_item = (
        db.query(OrderItem)
        .filter(
            OrderItem.order_id == order.id,
            OrderItem.variant_id == variant_id,
        )
        .first()
    )
    if existing_item is not None:
        existing_item.quantity = int(existing_item.quantity) + quantity
    else:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=variant.product_id,
                variant_id=variant.id,
                quantity=quantity,
                unit_price=float(variant.price),
                discount_id=None,
                discount_amount=0.0,
                final_unit_price=float(variant.price),
                line_total=float(variant.price) * quantity,
            )
        )

    db.flush()
    db.refresh(order)
    _recalculate_order_total(order, db=db)
    db.flush()
    db.refresh(order)
    return _order_to_dict(order)


def remove_item_from_draft_order(user_id: int, item_id: int, db: Session) -> dict | None:
    draft = (
        _order_query(db)
        .filter(
            Order.user_id == user_id,
            Order.status == "draft",
        )
        .order_by(Order.created_at.desc(), Order.id.desc())
        .with_for_update()
        .first()
    )
    if draft is None:
        return None
    if draft.status != "draft":
        raise ValueError("items can only be edited in draft status")

    item = (
        db.query(OrderItem)
        .filter(
            OrderItem.id == item_id,
            OrderItem.order_id == draft.id,
        )
        .first()
    )
    if item is None:
        return None

    db.delete(item)
    db.flush()
    db.refresh(draft)
    _recalculate_order_total(draft, db=db)
    db.flush()
    db.refresh(draft)
    return _order_to_dict(draft)


def change_order_status(
    user_id: int,
    order_id: int,
    new_status: str,
    db: Session,
    *,
    is_admin: bool = False,
    payment_ref: str | None = None,
    paid_amount: float | None = None,
) -> dict:
    if new_status not in ALLOWED_ORDER_STATUS:
        raise ValueError("invalid status")

    if new_status != "paid" and (payment_ref is not None or paid_amount is not None):
        raise ValueError("payment_ref and paid_amount are only valid when status is paid")

    order_filter = [Order.id == order_id]
    if not (is_admin and new_status == "paid"):
        order_filter.append(Order.user_id == user_id)

    order = (
        _order_query(db)
        .filter(*order_filter)
        .with_for_update()
        .first()
    )
    if order is None:
        raise LookupError("order not found")

    if order.status != "draft" and new_status == "draft":
        raise ValueError("cannot move non-draft order back to draft")

    if order.status == "draft" and new_status != "draft" and not order.items:
        raise ValueError("cannot leave draft with an empty order")

    if new_status == "paid":
        if not is_admin:
            raise ValueError("only admins can set status paid manually")
        if payment_ref is None or not payment_ref.strip():
            raise ValueError("payment_ref is required when status is paid")
        if paid_amount is None or float(paid_amount) <= 0:
            raise ValueError("paid_amount must be greater than 0 when status is paid")

        confirm_manual_payment_for_order(
            order_id=order.id,
            user_id=order.user_id,
            payment_ref=payment_ref,
            paid_amount=float(paid_amount),
            db=db,
        )
        db.flush()
        db.refresh(order)
        return _order_to_dict(order)

    if order.status == new_status:
        return _order_to_dict(order)

    if order.status == "draft" and new_status == "submitted":
        _recalculate_order_total(order, db=db, force=True)
        validate_order_pricing_before_submit(_order_to_dict(order))
        order.pricing_frozen = True
        if order.pricing_frozen_at is None:
            order.pricing_frozen_at = _utc_now()
        if order.submitted_at is None:
            order.submitted_at = _utc_now()

    if new_status == "cancelled" and order.cancelled_at is None:
        order.cancelled_at = _utc_now()

    order.status = new_status
    db.flush()
    db.refresh(order)
    return _order_to_dict(order)


def pay_order(
    user_id: int,
    order_id: int,
    payment_ref: str,
    paid_amount: float,
    db: Session,
) -> dict:
    confirm_manual_payment_for_order(
        order_id=order_id,
        user_id=user_id,
        payment_ref=payment_ref,
        paid_amount=paid_amount,
        db=db,
    )
    order = (
        _order_query(db)
        .filter(
            Order.id == order_id,
            Order.user_id == user_id,
        )
        .first()
    )
    if order is None:
        raise LookupError("order not found")
    return _order_to_dict(order)


def create_manual_submitted_order(
    *,
    email: str,
    first_name: str,
    last_name: str,
    phone: str,
    items: list[dict],
    db: Session,
) -> dict:
    if not items:
        raise ValueError("items are required")

    user, user_created = get_or_create_user_by_contact(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        db=db,
    )

    order = Order(
        user_id=int(user.id),
        status="draft",
        currency="ARS",
        subtotal=0.0,
        discount_total=0.0,
        total_amount=0.0,
        pricing_frozen=False,
    )
    db.add(order)
    db.flush()

    aggregated_items: dict[int, int] = {}
    for item in items:
        variant_id = int(item["variant_id"])
        quantity = int(item["quantity"])
        if quantity <= 0:
            raise ValueError("quantity must be greater than 0")
        aggregated_items[variant_id] = aggregated_items.get(variant_id, 0) + quantity

    for variant_id, quantity in aggregated_items.items():
        variant = (
            db.query(ProductVariant)
            .options(joinedload(ProductVariant.product))
            .filter(
                ProductVariant.id == variant_id,
                ProductVariant.is_active.is_(True),
            )
            .first()
        )
        if variant is None:
            raise ValueError(f"variant {variant_id} not found")

        db.add(
            OrderItem(
                order_id=order.id,
                product_id=variant.product_id,
                variant_id=variant.id,
                quantity=quantity,
                unit_price=float(variant.price),
                discount_id=None,
                discount_amount=0.0,
                final_unit_price=float(variant.price),
                line_total=float(variant.price) * quantity,
            )
        )

    db.flush()
    db.refresh(order)
    _recalculate_order_total(order, db=db, force=True)
    validate_order_pricing_before_submit(_order_to_dict(order))
    order.pricing_frozen = True
    if order.pricing_frozen_at is None:
        order.pricing_frozen_at = _utc_now()
    if order.submitted_at is None:
        order.submitted_at = _utc_now()
    order.status = "submitted"
    db.flush()
    db.refresh(order)

    return {
        "customer": serialize_user_basic(user),
        "order": _order_to_dict(order),
        "meta": {"user_created": user_created},
    }

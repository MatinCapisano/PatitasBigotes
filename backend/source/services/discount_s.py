from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, TypedDict

from sqlalchemy.orm import Session, joinedload

from source.db.models import Discount, DiscountProduct, Product
from source.db.session import SessionLocal

ALLOWED_DISCOUNT_TYPES = {"percent", "fixed"}
ALLOWED_DISCOUNT_SCOPES = {"all", "category", "product", "product_list"}


class DiscountDTO(TypedDict):
    id: int
    name: str
    type: str
    value: float
    scope: str
    scope_value: str | int | None
    is_active: bool
    starts_at: datetime | None
    ends_at: datetime | None
    product_ids: list[int]


@contextmanager
def _session_scope(db: Session | None):
    owns_session = db is None
    session = db or SessionLocal()
    try:
        yield session, owns_session
    finally:
        if owns_session:
            session.close()


def _coerce_datetime(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _discount_to_dict(discount: Discount) -> DiscountDTO:
    product_ids = [link.product_id for link in discount.product_links]
    return {
        "id": discount.id,
        "name": discount.name,
        "type": discount.type,
        "value": float(discount.value),
        "scope": discount.scope,
        "scope_value": discount.scope_value,
        "is_active": bool(discount.is_active),
        "starts_at": discount.starts_at,
        "ends_at": discount.ends_at,
        "product_ids": product_ids,
    }


def list_discounts(db: Session | None = None) -> list[DiscountDTO]:
    with _session_scope(db) as (session, _):
        discounts = (
            session.query(Discount)
            .options(joinedload(Discount.product_links))
            .order_by(Discount.id.asc())
            .all()
        )
        return [_discount_to_dict(discount) for discount in discounts]


def get_discount_by_id(discount_id: int, db: Session | None = None) -> DiscountDTO | None:
    with _session_scope(db) as (session, _):
        discount = (
            session.query(Discount)
            .options(joinedload(Discount.product_links))
            .filter(Discount.id == discount_id)
            .first()
        )
        if discount is None:
            return None
        return _discount_to_dict(discount)


def _set_discount_product_list(db: Session, discount: Discount, product_ids: list[int]) -> None:
    unique_ids = list(dict.fromkeys(product_ids))
    if unique_ids:
        existing_count = (
            db.query(Product.id)
            .filter(Product.id.in_(unique_ids))
            .count()
        )
        if existing_count != len(unique_ids):
            raise ValueError("one or more product_ids do not exist")

    db.query(DiscountProduct).filter(DiscountProduct.discount_id == discount.id).delete()
    for product_id in unique_ids:
        db.add(DiscountProduct(discount_id=discount.id, product_id=product_id))


def create_discount(payload: dict, db: Session | None = None) -> DiscountDTO:
    _validate_discount_payload(payload)

    with _session_scope(db) as (session, owns_session):
        discount = Discount(
            name=payload["name"],
            type=payload["type"],
            value=float(payload["value"]),
            scope=payload["scope"],
            scope_value=payload.get("scope_value"),
            is_active=bool(payload.get("is_active", True)),
            starts_at=_coerce_datetime(payload.get("starts_at")),
            ends_at=_coerce_datetime(payload.get("ends_at")),
        )
        session.add(discount)
        session.flush()

        if discount.scope == "product_list":
            _set_discount_product_list(
                db=session,
                discount=discount,
                product_ids=payload.get("product_ids", []),
            )

        if owns_session:
            session.commit()
        else:
            session.flush()
        session.refresh(discount)
        return get_discount_by_id(discount.id, db=session)


def update_discount(discount_id: int, updates: dict, db: Session | None = None) -> DiscountDTO | None:
    with _session_scope(db) as (session, owns_session):
        discount = session.query(Discount).filter(Discount.id == discount_id).first()
        if discount is None:
            return None

        current = get_discount_by_id(discount_id=discount_id, db=session)
        if current is None:
            return None

        merged = {**current, **updates}
        _validate_discount_payload(merged)

        discount.name = merged["name"]
        discount.type = merged["type"]
        discount.value = float(merged["value"])
        discount.scope = merged["scope"]
        discount.scope_value = merged.get("scope_value")
        discount.is_active = bool(merged.get("is_active", True))
        discount.starts_at = _coerce_datetime(merged.get("starts_at"))
        discount.ends_at = _coerce_datetime(merged.get("ends_at"))

        if merged["scope"] == "product_list":
            _set_discount_product_list(
                db=session,
                discount=discount,
                product_ids=merged.get("product_ids", []),
            )
        else:
            session.query(DiscountProduct).filter(DiscountProduct.discount_id == discount.id).delete()

        if owns_session:
            session.commit()
        else:
            session.flush()
        session.refresh(discount)
        return get_discount_by_id(discount_id, db=session)


def delete_discount(discount_id: int, db: Session | None = None) -> DiscountDTO | None:
    with _session_scope(db) as (session, owns_session):
        discount = (
            session.query(Discount)
            .options(joinedload(Discount.product_links))
            .filter(Discount.id == discount_id)
            .first()
        )
        if discount is None:
            return None
        serialized = _discount_to_dict(discount)
        session.delete(discount)
        if owns_session:
            session.commit()
        else:
            session.flush()
        return serialized


def _validate_discount_payload(payload: dict) -> None:
    discount_type = payload.get("type")
    scope = payload.get("scope")
    value = payload.get("value")
    scope_value = payload.get("scope_value")
    product_ids = payload.get("product_ids", [])

    if discount_type not in ALLOWED_DISCOUNT_TYPES:
        raise ValueError("invalid discount type")
    if scope not in ALLOWED_DISCOUNT_SCOPES:
        raise ValueError("invalid discount scope")
    if value is None or float(value) <= 0:
        raise ValueError("discount value must be greater than 0")
    if discount_type == "percent" and float(value) > 100:
        raise ValueError("percent discount cannot exceed 100")

    if scope == "all" and scope_value is not None:
        raise ValueError("scope_value must be null for all scope")
    if scope in {"category", "product"} and scope_value is None:
        raise ValueError("scope_value is required for category/product scope")
    if scope == "product_list":
        if scope_value is not None:
            raise ValueError("scope_value must be null for product_list scope")
        if not product_ids:
            raise ValueError("product_ids is required for product_list scope")


# Core (pure logic)
def is_discount_currently_valid(discount: DiscountDTO, at: datetime | None = None) -> bool:
    now = at or datetime.utcnow()
    if not discount.get("is_active", False):
        return False

    starts_at = _coerce_datetime(discount.get("starts_at"))
    ends_at = _coerce_datetime(discount.get("ends_at"))

    if starts_at is not None and now < starts_at:
        return False
    if ends_at is not None and now > ends_at:
        return False
    return True


def select_best_discount(discounts: Iterable[DiscountDTO], unit_price: float) -> DiscountDTO | None:
    best: DiscountDTO | None = None
    best_amount = 0.0

    for discount in discounts:
        amount = calculate_line_discount(unit_price=unit_price, discount=discount)
        if amount > best_amount:
            best = discount
            best_amount = amount

    return best


def calculate_line_discount(unit_price: float, discount: DiscountDTO) -> float:
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


def calculate_line_pricing(unit_price: float, quantity: int, discount: DiscountDTO | None) -> dict:
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


def get_applicable_discounts_for_product(product: dict, discounts: Iterable[DiscountDTO]) -> list[DiscountDTO]:
    applicable: list[DiscountDTO] = []
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


def set_discount_product_list(discount: DiscountDTO, product_ids: list[int]) -> DiscountDTO:
    discount["product_ids"] = list(dict.fromkeys(product_ids))
    return discount


def add_products_to_discount(discount: DiscountDTO, product_ids: list[int]) -> DiscountDTO:
    current = set(discount.get("product_ids", []))
    current.update(product_ids)
    discount["product_ids"] = sorted(current)
    return discount


def remove_products_from_discount(discount: DiscountDTO, product_ids: list[int]) -> DiscountDTO:
    to_remove = set(product_ids)
    current = [pid for pid in discount.get("product_ids", []) if pid not in to_remove]
    discount["product_ids"] = current
    return discount


# Order orchestration helpers
def reprice_order_items(order: dict, discounts: Iterable[DiscountDTO], products_by_id: dict[int, dict]) -> dict:
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

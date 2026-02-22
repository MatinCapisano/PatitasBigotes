from __future__ import annotations

from contextlib import contextmanager
from typing import Literal

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from source.db.models import Category, Product, ProductVariant
from source.db.session import SessionLocal


@contextmanager
def _session_scope(db: Session | None):
    owns_session = db is None
    session = db or SessionLocal()
    try:
        yield session, owns_session
    finally:
        if owns_session:
            session.close()


def _product_inventory(product: Product) -> tuple[int, int]:
    active_variants = [variant for variant in product.variants if variant.is_active]
    total_stock = sum(int(variant.stock) for variant in active_variants)
    active_flag = 1 if active_variants else 0
    return total_stock, active_flag


def _product_to_dict(product: Product) -> dict:
    stock, active = _product_inventory(product)
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "category": product.category.name if product.category is not None else None,
        "stock": stock,
        "active": active,
    }


def _variant_to_dict(variant: ProductVariant) -> dict:
    return {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": variant.sku,
        "size": variant.size,
        "color": variant.color,
        "price": float(variant.price),
        "stock": int(variant.stock),
        "active": 1 if variant.is_active else 0,
    }


def _build_default_sku(session: Session, product_id: int) -> str:
    base = f"PRODUCT-{product_id}-DEFAULT"
    sku = base
    suffix = 1
    while session.query(ProductVariant.id).filter(ProductVariant.sku == sku).first() is not None:
        suffix += 1
        sku = f"{base}-{suffix}"
    return sku


def _ensure_default_variant_for_product(session: Session, product: Product) -> ProductVariant:
    for variant in product.variants:
        if variant.is_active:
            return variant

    default_variant = ProductVariant(
        product_id=product.id,
        sku=_build_default_sku(session=session, product_id=product.id),
        size=None,
        color=None,
        price=float(product.price),
        stock=0,
        is_active=True,
    )
    session.add(default_variant)
    session.flush()
    session.refresh(product)
    return default_variant


def filter_and_sort_products(
    db: Session | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    category: str | None = None,
    sort_by: Literal["price", "name"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> list[dict]:
    with _session_scope(db) as (session, _):
        query = session.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.variants),
        )

        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        if category is not None:
            query = query.join(Product.category).filter_by(name=category)

        if sort_by is not None:
            column = Product.price if sort_by == "price" else Product.name
            query = query.order_by(desc(column) if sort_order == "desc" else asc(column))
        else:
            query = query.order_by(Product.id.asc())

        return [_product_to_dict(product) for product in query.all()]


def get_product_by_id(product_id: int, db: Session | None = None) -> dict | None:
    with _session_scope(db) as (session, _):
        product = (
            session.query(Product)
            .options(joinedload(Product.category), joinedload(Product.variants))
            .filter(Product.id == product_id)
            .first()
        )
        if product is None:
            return None
        return _product_to_dict(product)


def update_product(product_id: int, updates: dict, db: Session | None = None) -> dict | None:
    allowed_fields = {"name", "description", "price", "category", "active"}
    with _session_scope(db) as (session, owns_session):
        product = (
            session.query(Product)
            .options(joinedload(Product.category), joinedload(Product.variants))
            .filter(Product.id == product_id)
            .first()
        )
        if product is None:
            return None

        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            if field == "category":
                category = session.query(Category).filter(Category.name == str(value)).first()
                if category is None:
                    raise ValueError("category not found")
                product.category_id = category.id
            elif field == "active":
                active_flag = bool(value)
                if active_flag:
                    _ensure_default_variant_for_product(session=session, product=product)
                    for variant in product.variants:
                        variant.is_active = True
                else:
                    for variant in product.variants:
                        variant.is_active = False
            elif field == "price":
                product.price = float(value)
            else:
                setattr(product, field, value)

        session.flush()
        if owns_session:
            session.commit()
        session.refresh(product)
        return _product_to_dict(product)


def deactivate_product(product_id: int, db: Session | None = None) -> dict | None:
    return update_product(product_id=product_id, updates={"active": 0}, db=db)


def activate_product(product_id: int, db: Session | None = None) -> dict | None:
    return update_product(product_id=product_id, updates={"active": 1}, db=db)


def ensure_product_has_variant(product_id: int, db: Session | None = None) -> list[dict]:
    with _session_scope(db) as (session, owns_session):
        product = (
            session.query(Product)
            .options(joinedload(Product.variants))
            .filter(Product.id == product_id)
            .first()
        )
        if product is None:
            raise LookupError("product not found")

        active_variants = [variant for variant in product.variants if variant.is_active]
        if active_variants:
            return [_variant_to_dict(variant) for variant in active_variants]

        created = _ensure_default_variant_for_product(session=session, product=product)
        if owns_session:
            session.commit()
        return [_variant_to_dict(created)]


def add_stock(product_id: int, quantity: int, db: Session | None = None) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _session_scope(db) as (session, owns_session):
        variants = ensure_product_has_variant(product_id=product_id, db=session)
        if not variants:
            raise ValueError("product has no active variants")

        add_variant_stock(variant_id=variants[0]["id"], quantity=quantity, db=session)
        if owns_session:
            session.commit()

        product = get_product_by_id(product_id=product_id, db=session)
        if product is None:
            raise LookupError("product not found")
        return product


def decrement_stock(product_id: int, quantity: int, db: Session | None = None) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _session_scope(db) as (session, owns_session):
        product = (
            session.query(Product)
            .options(joinedload(Product.variants), joinedload(Product.category))
            .filter(Product.id == product_id)
            .first()
        )
        if product is None:
            raise LookupError("product not found")

        active_variants = [variant for variant in product.variants if variant.is_active]
        total_stock = sum(int(variant.stock) for variant in active_variants)
        if total_stock < quantity:
            raise ValueError("insufficient stock")

        remaining = quantity
        for variant in active_variants:
            if remaining == 0:
                break
            current_stock = int(variant.stock)
            if current_stock == 0:
                continue
            taken = min(current_stock, remaining)
            variant.stock = current_stock - taken
            remaining -= taken

        session.flush()
        if owns_session:
            session.commit()

        return _product_to_dict(product)


def get_variant_by_id(variant_id: int, db: Session | None = None) -> dict | None:
    with _session_scope(db) as (session, _):
        variant = (
            session.query(ProductVariant)
            .options(joinedload(ProductVariant.product).joinedload(Product.category))
            .filter(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True))
            .first()
        )
        if variant is None or variant.product is None:
            return None
        return _variant_to_dict(variant)


def list_variants_by_product_id(product_id: int, db: Session | None = None) -> list[dict]:
    with _session_scope(db) as (session, _):
        variants = (
            session.query(ProductVariant)
            .filter(
                ProductVariant.product_id == product_id,
                ProductVariant.is_active.is_(True),
            )
            .order_by(ProductVariant.id.asc())
            .all()
        )
        return [_variant_to_dict(variant) for variant in variants]


def add_variant_stock(variant_id: int, quantity: int, db: Session | None = None) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _session_scope(db) as (session, owns_session):
        variant = (
            session.query(ProductVariant)
            .filter(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True))
            .first()
        )
        if variant is None:
            raise LookupError("variant not found")

        variant.stock = int(variant.stock) + quantity
        session.flush()
        if owns_session:
            session.commit()
        return _variant_to_dict(variant)


def decrement_variant_stock(variant_id: int, quantity: int, db: Session | None = None) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _session_scope(db) as (session, owns_session):
        variant = (
            session.query(ProductVariant)
            .filter(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True))
            .first()
        )
        if variant is None:
            raise LookupError("variant not found")

        current_stock = int(variant.stock)
        if current_stock < quantity:
            raise ValueError("insufficient stock")

        variant.stock = current_stock - quantity
        session.flush()
        if owns_session:
            session.commit()
        return _variant_to_dict(variant)

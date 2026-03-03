from __future__ import annotations

from contextlib import contextmanager
from typing import Literal

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session, joinedload

from source.db.models import Category, Product, ProductVariant
from source.db.session import SessionLocal


@contextmanager
def _read_session_scope(db: Session | None):
    owns_session = db is None
    session = db or SessionLocal()
    try:
        yield session, owns_session
    finally:
        if owns_session:
            session.close()


@contextmanager
def _write_session_scope(db: Session):
    if db is None:
        raise RuntimeError("db session is required for mutating operations")
    yield db, False


def _product_inventory(product: Product) -> tuple[int, int]:
    active_variants = [variant for variant in product.variants if variant.is_active]
    total_stock = sum(int(variant.stock) for variant in active_variants)
    active_flag = 1 if active_variants else 0
    return total_stock, active_flag


def _compute_min_var_price(product: Product) -> int | None:
    prices = [int(variant.price) for variant in product.variants if variant.is_active]
    if not prices:
        return None
    return int(min(prices))


def _product_to_dict(product: Product) -> dict:
    stock, active = _product_inventory(product)
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "min_var_price": _compute_min_var_price(product),
        "category_id": product.category_id,
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
        "price": int(variant.price),
        "stock": int(variant.stock),
        "active": 1 if variant.is_active else 0,
    }


def _category_to_dict(category: Category) -> dict:
    return {
        "id": int(category.id),
        "name": category.name,
    }


def filter_and_sort_products(
    db: Session | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    category: str | None = None,
    sort_by: Literal["price", "name"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
) -> list[dict]:
    with _read_session_scope(db) as (session, _):
        min_price_subquery = (
            session.query(
                ProductVariant.product_id.label("product_id"),
                func.min(ProductVariant.price).label("min_var_price"),
            )
            .filter(ProductVariant.is_active.is_(True))
            .group_by(ProductVariant.product_id)
            .subquery()
        )

        query = (
            session.query(Product, min_price_subquery.c.min_var_price)
            .outerjoin(min_price_subquery, Product.id == min_price_subquery.c.product_id)
            .options(
                joinedload(Product.category),
                joinedload(Product.variants),
            )
        )

        if min_price is not None:
            query = query.filter(min_price_subquery.c.min_var_price >= min_price)
        if max_price is not None:
            query = query.filter(min_price_subquery.c.min_var_price <= max_price)
        if category is not None:
            query = query.join(Product.category).filter_by(name=category)

        if sort_by is not None:
            column = min_price_subquery.c.min_var_price if sort_by == "price" else Product.name
            query = query.order_by(desc(column) if sort_order == "desc" else asc(column))
        else:
            query = query.order_by(Product.id.asc())

        return [_product_to_dict(product) for product, _ in query.all()]


def get_product_by_id(product_id: int, db: Session | None = None) -> dict | None:
    with _read_session_scope(db) as (session, _):
        product = (
            session.query(Product)
            .options(joinedload(Product.category), joinedload(Product.variants))
            .filter(Product.id == product_id)
            .first()
        )
        if product is None:
            return None
        return _product_to_dict(product)


def update_product(product_id: int, updates: dict, db: Session) -> dict | None:
    allowed_fields = {"name", "description", "category", "active"}
    with _write_session_scope(db) as (session, _):
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
                    for variant in product.variants:
                        variant.is_active = True
                else:
                    for variant in product.variants:
                        variant.is_active = False
            else:
                setattr(product, field, value)

        session.flush()
        session.refresh(product)
        return _product_to_dict(product)


def create_product(payload: dict, db: Session) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("name is required")

    category_name = str(payload.get("category", "")).strip()
    if not category_name:
        raise ValueError("category is required")

    description = payload.get("description")
    normalized_description = None if description is None else str(description).strip() or None

    with _write_session_scope(db) as (session, _):
        category = session.query(Category).filter(Category.name == category_name).first()
        if category is None:
            raise ValueError("category not found")

        product = Product(
            name=name,
            description=normalized_description,
            category_id=category.id,
        )
        session.add(product)
        session.flush()

        session.refresh(product)
        return _product_to_dict(product)


def delete_product_hard(product_id: int, db: Session) -> dict | None:
    with _write_session_scope(db) as (session, _):
        product = (
            session.query(Product)
            .options(joinedload(Product.category), joinedload(Product.variants))
            .filter(Product.id == product_id)
            .first()
        )
        if product is None:
            return None

        product_data = _product_to_dict(product)
        session.delete(product)
        session.flush()
        return product_data


def deactivate_product(product_id: int, db: Session) -> dict | None:
    return update_product(product_id=product_id, updates={"active": 0}, db=db)


def activate_product(product_id: int, db: Session) -> dict | None:
    return update_product(product_id=product_id, updates={"active": 1}, db=db)


def ensure_product_has_variant(product_id: int, db: Session | None = None) -> list[dict]:
    with _read_session_scope(db) as (session, _):
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

        raise LookupError("product has no active variants")


def add_stock(product_id: int, quantity: int, db: Session) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _write_session_scope(db) as (session, _):
        variants = ensure_product_has_variant(product_id=product_id, db=session)
        if not variants:
            raise ValueError("product has no active variants")

        add_variant_stock(variant_id=variants[0]["id"], quantity=quantity, db=session)

        product = get_product_by_id(product_id=product_id, db=session)
        if product is None:
            raise LookupError("product not found")
        return product


def decrement_stock(product_id: int, quantity: int, db: Session) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _write_session_scope(db) as (session, _):
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

        return _product_to_dict(product)


def get_variant_by_id(
    variant_id: int,
    db: Session | None = None,
    *,
    include_inactive: bool = False,
) -> dict | None:
    with _read_session_scope(db) as (session, _):
        query = (
            session.query(ProductVariant)
            .options(joinedload(ProductVariant.product).joinedload(Product.category))
            .filter(ProductVariant.id == variant_id)
        )
        if not include_inactive:
            query = query.filter(ProductVariant.is_active.is_(True))
        variant = query.first()
        if variant is None or variant.product is None:
            return None
        return _variant_to_dict(variant)


def list_variants_by_product_id(
    product_id: int,
    db: Session | None = None,
    *,
    include_inactive: bool = False,
) -> list[dict]:
    with _read_session_scope(db) as (session, _):
        query = (
            session.query(ProductVariant)
            .filter(
                ProductVariant.product_id == product_id,
            )
            .order_by(ProductVariant.id.asc())
        )
        if not include_inactive:
            query = query.filter(ProductVariant.is_active.is_(True))
        variants = query.all()
        return [_variant_to_dict(variant) for variant in variants]


def list_categories(db: Session | None = None) -> list[dict]:
    with _read_session_scope(db) as (session, _):
        categories = session.query(Category).order_by(Category.id.asc()).all()
        return [_category_to_dict(category) for category in categories]


def get_category_by_id(category_id: int, db: Session | None = None) -> dict | None:
    with _read_session_scope(db) as (session, _):
        category = session.query(Category).filter(Category.id == category_id).first()
        if category is None:
            return None
        return _category_to_dict(category)


def create_category(payload: dict, db: Session) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise ValueError("name is required")

    with _write_session_scope(db) as (session, _):
        existing = session.query(Category).filter(Category.name == name).first()
        if existing is not None:
            raise ValueError("category already exists")

        category = Category(name=name)
        session.add(category)
        session.flush()
        return _category_to_dict(category)


def update_category(category_id: int, updates: dict, db: Session) -> dict | None:
    with _write_session_scope(db) as (session, _):
        category = session.query(Category).filter(Category.id == category_id).first()
        if category is None:
            return None

        if "name" in updates:
            new_name = str(updates.get("name", "")).strip()
            if not new_name:
                raise ValueError("name is required")
            duplicate = (
                session.query(Category)
                .filter(Category.name == new_name, Category.id != category_id)
                .first()
            )
            if duplicate is not None:
                raise ValueError("category already exists")
            category.name = new_name

        session.flush()
        return _category_to_dict(category)


def delete_category_hard(category_id: int, db: Session) -> dict | None:
    with _write_session_scope(db) as (session, _):
        category = session.query(Category).filter(Category.id == category_id).first()
        if category is None:
            return None
        payload = _category_to_dict(category)
        session.delete(category)
        session.flush()
        return payload


def create_variant(payload: dict, db: Session) -> dict:
    try:
        product_id = int(payload.get("product_id"))
    except (TypeError, ValueError) as exc:
        raise ValueError("product_id is required") from exc
    sku = str(payload.get("sku", "")).strip()
    if not sku:
        raise ValueError("sku is required")

    try:
        price = int(payload.get("price"))
    except (TypeError, ValueError) as exc:
        raise ValueError("price is required") from exc
    try:
        stock = int(payload.get("stock", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("stock must be greater than or equal to 0") from exc
    if price < 0:
        raise ValueError("price must be greater than or equal to 0")
    if stock < 0:
        raise ValueError("stock must be greater than or equal to 0")

    with _write_session_scope(db) as (session, _):
        product = session.query(Product).filter(Product.id == product_id).first()
        if product is None:
            raise ValueError("product not found")

        existing = session.query(ProductVariant).filter(ProductVariant.sku == sku).first()
        if existing is not None:
            raise ValueError("variant sku already exists")

        variant = ProductVariant(
            product_id=product_id,
            sku=sku,
            size=None if payload.get("size") is None else str(payload.get("size")).strip() or None,
            color=None if payload.get("color") is None else str(payload.get("color")).strip() or None,
            price=price,
            stock=stock,
            is_active=bool(payload.get("active", True)),
        )
        session.add(variant)
        session.flush()
        return _variant_to_dict(variant)


def update_variant(variant_id: int, updates: dict, db: Session) -> dict | None:
    allowed_fields = {"product_id", "sku", "size", "color", "price", "stock", "active"}
    with _write_session_scope(db) as (session, _):
        variant = session.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
        if variant is None:
            return None

        for field, value in updates.items():
            if field not in allowed_fields:
                continue
            if field == "product_id":
                try:
                    product_id = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("product_id is required") from exc
                product = session.query(Product).filter(Product.id == product_id).first()
                if product is None:
                    raise ValueError("product not found")
                variant.product_id = product_id
            elif field == "sku":
                sku = str(value).strip()
                if not sku:
                    raise ValueError("sku is required")
                duplicate = (
                    session.query(ProductVariant)
                    .filter(ProductVariant.sku == sku, ProductVariant.id != variant_id)
                    .first()
                )
                if duplicate is not None:
                    raise ValueError("variant sku already exists")
                variant.sku = sku
            elif field == "size":
                variant.size = None if value is None else str(value).strip() or None
            elif field == "color":
                variant.color = None if value is None else str(value).strip() or None
            elif field == "price":
                try:
                    price = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("price is required") from exc
                if price < 0:
                    raise ValueError("price must be greater than or equal to 0")
                variant.price = price
            elif field == "stock":
                try:
                    stock = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("stock must be greater than or equal to 0") from exc
                if stock < 0:
                    raise ValueError("stock must be greater than or equal to 0")
                variant.stock = stock
            elif field == "active":
                variant.is_active = bool(value)

        session.flush()
        return _variant_to_dict(variant)


def delete_variant_hard(variant_id: int, db: Session) -> dict | None:
    with _write_session_scope(db) as (session, _):
        variant = session.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
        if variant is None:
            return None
        payload = _variant_to_dict(variant)
        session.delete(variant)
        session.flush()
        return payload


def add_variant_stock(variant_id: int, quantity: int, db: Session) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _write_session_scope(db) as (session, _):
        variant = (
            session.query(ProductVariant)
            .filter(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True))
            .first()
        )
        if variant is None:
            raise LookupError("variant not found")

        variant.stock = int(variant.stock) + quantity
        session.flush()
        return _variant_to_dict(variant)


def decrement_variant_stock(variant_id: int, quantity: int, db: Session) -> dict:
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    with _write_session_scope(db) as (session, _):
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
        return _variant_to_dict(variant)

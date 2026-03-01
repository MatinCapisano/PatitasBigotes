from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )

    category = relationship("Category", back_populates="products")
    discount_links = relationship("DiscountProduct", back_populates="product")
    variants = relationship("ProductVariant", back_populates="product")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    sku = Column(String, nullable=False, unique=True, index=True)
    size = Column(String, nullable=True)
    color = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    product = relationship("Product", back_populates="variants")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    email = Column(String, nullable=False, unique=True, index=True)
    dni = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    has_account = Column(Boolean, default=False, nullable=False)

    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    orders = relationship("Order", back_populates="user")
    turns = relationship("Turn", back_populates="user")
    refresh_session = relationship(
        "UserRefreshSession",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Turn(Base):
    __tablename__ = "turns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(String, nullable=False, default="pending")
    scheduled_at = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="turns")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status = Column(String, nullable=False, default="draft")
    currency = Column(String, nullable=False, default="ARS")
    subtotal = Column(Float, nullable=False, default=0)
    discount_total = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)
    pricing_frozen = Column(Boolean, nullable=False, default=False)
    pricing_frozen_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="orders")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    stock_reservations = relationship(
        "StockReservation",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    variant_id = Column(
        Integer,
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_id = Column(
        Integer,
        ForeignKey("discounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    discount_amount = Column(Float, nullable=False, default=0)
    final_unit_price = Column(Float, nullable=False, default=0)
    line_total = Column(Float, nullable=False, default=0)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
    discount = relationship("Discount")
    stock_reservations = relationship(
        "StockReservation",
        back_populates="order_item",
        cascade="all, delete-orphan",
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index(
            "uq_payments_one_pending_per_order_method",
            "order_id",
            "method",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    method = Column(String, nullable=False)  # bank_transfer | mercadopago
    status = Column(String, nullable=False, default="pending")
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="ARS")

    idempotency_key = Column(String, nullable=False, unique=True, index=True)
    external_ref = Column(String, nullable=True, index=True)
    provider_status = Column(String, nullable=True)
    provider_payload = Column(String, nullable=True)
    receipt_url = Column(String, nullable=True)

    expires_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    order = relationship("Order", back_populates="payments")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)
    event_key = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False, default="processing")
    payload = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)


class StockReservation(Base):
    __tablename__ = "stock_reservations"
    __table_args__ = (
        Index(
            "ix_stock_reservations_variant_status_expires",
            "variant_id",
            "status",
            "expires_at",
        ),
        Index("ix_stock_reservations_order_status", "order_id", "status"),
        Index("ix_stock_reservations_status_expires", "status", "expires_at"),
        Index(
            "uq_stock_reservation_active_per_item",
            "order_item_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        CheckConstraint("quantity > 0", name="ck_stock_reservations_quantity_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id = Column(
        Integer,
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id = Column(
        Integer,
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="active")
    reactivation_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    order = relationship("Order", back_populates="stock_reservations")
    order_item = relationship("OrderItem", back_populates="stock_reservations")
    variant = relationship("ProductVariant")


class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # percent | fixed
    value = Column(Float, nullable=False)

    scope = Column(String, nullable=False)  # all | category | product | product_list
    scope_value = Column(String, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    product_links = relationship("DiscountProduct", back_populates="discount")


class DiscountProduct(Base):
    __tablename__ = "discount_products"

    discount_id = Column(
        Integer,
        ForeignKey("discounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )

    discount = relationship("Discount", back_populates="product_links")
    product = relationship("Product", back_populates="discount_links")


class UserRefreshSession(Base):
    __tablename__ = "user_refresh_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    token_hash = Column(String, nullable=False)
    token_jti = Column(String, nullable=False, index=True)
    claim_sub = Column(String, nullable=False)
    claim_type = Column(String, nullable=False)
    claim_iss = Column(String, nullable=False)
    claim_iat = Column(DateTime, nullable=False)
    claim_exp = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="refresh_session")

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
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
    price = Column(Float, nullable=False)

    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )

    category = relationship("Category", back_populates="products")
    discount_links = relationship("DiscountProduct", back_populates="product")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    email = Column(String, nullable=False, unique=True, index=True)
    phone = Column(String, nullable=True)

    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    orders = relationship("Order", back_populates="user")
    turns = relationship("Turn", back_populates="user")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status = Column(String, nullable=False, default="draft")
    subtotal = Column(Float, nullable=False, default=0)
    discount_total = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)
    pricing_frozen = Column(Boolean, nullable=False, default=False)
    pricing_frozen_at = Column(DateTime, nullable=True)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


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
    discount = relationship("Discount")


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

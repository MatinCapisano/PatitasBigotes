from source.schemas.auth_s import LoginRequest
from source.schemas.discounts_s import CreateDiscountRequest, UpdateDiscountRequest
from source.schemas.orders_s import (
    AddOrderItemRequest,
    PayOrderRequest,
    UpdateOrderStatusRequest,
)
from source.schemas.payments_s import CreateOrderPaymentRequest
from source.schemas.products_s import (
    CreateProductRequest,
    PatchProductRequest,
    UpdateProductRequest,
)
from source.schemas.turns_s import CreateTurnRequest
from source.schemas.users_s import CreateUserRequest

__all__ = [
    "AddOrderItemRequest",
    "UpdateOrderStatusRequest",
    "CreateUserRequest",
    "LoginRequest",
    "UpdateDiscountRequest",
    "CreateDiscountRequest",
    "PayOrderRequest",
    "CreateOrderPaymentRequest",
    "CreateProductRequest",
    "UpdateProductRequest",
    "PatchProductRequest",
    "CreateTurnRequest",
]

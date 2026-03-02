from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def round_half_up_decimal(value: Decimal, decimals: int = 2) -> Decimal:
    if decimals < 0:
        raise ValueError("decimals must be greater than or equal to 0")
    quantizer = Decimal("1").scaleb(-decimals)
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def decimal_to_cents(value: Decimal) -> int:
    rounded = round_half_up_decimal(value, decimals=2)
    return int(rounded * 100)


def parse_amount_to_cents(value: int | str | Decimal) -> int:
    if isinstance(value, int):
        if value < 0:
            raise ValueError("amount must be greater than or equal to 0")
        return value
    if isinstance(value, Decimal):
        cents = decimal_to_cents(value)
        if cents < 0:
            raise ValueError("amount must be greater than or equal to 0")
        return cents
    try:
        parsed = Decimal(str(value).strip())
    except Exception as exc:
        raise ValueError("invalid monetary amount") from exc
    cents = decimal_to_cents(parsed)
    if cents < 0:
        raise ValueError("amount must be greater than or equal to 0")
    return cents


def cents_to_decimal(value_cents: int) -> Decimal:
    return Decimal(value_cents) / Decimal(100)


def calcular_amount(
    unit_price: int,
    quantity: int,
    discount_type: str | None = None,
    discount_value: int | str | Decimal | None = None,
) -> dict:
    if unit_price < 0:
        raise ValueError("unit_price must be greater than or equal to 0")
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    if discount_type not in {None, "percent", "fixed"}:
        raise ValueError("invalid discount_type")

    discount_amount = 0
    if discount_type == "percent":
        if discount_value is None:
            raise ValueError("discount_value is required for percent discount")
        percent = Decimal(str(discount_value).strip())
        if percent < 0:
            raise ValueError("discount_value must be greater than or equal to 0")
        unit_price_decimal = cents_to_decimal(unit_price)
        discount_decimal = round_half_up_decimal(
            unit_price_decimal * (percent / Decimal(100)),
            decimals=2,
        )
        discount_amount = decimal_to_cents(discount_decimal)
    elif discount_type == "fixed":
        if discount_value is None:
            raise ValueError("discount_value is required for fixed discount")
        discount_amount = parse_amount_to_cents(discount_value)

    if discount_amount > unit_price:
        discount_amount = unit_price

    final_unit_price = unit_price - discount_amount
    line_total = final_unit_price * quantity

    return {
        "unit_price": unit_price,
        "quantity": quantity,
        "discount_amount": discount_amount,
        "final_unit_price": final_unit_price,
        "line_total": line_total,
    }

import sys
import unittest
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.services.money_s import calcular_amount, decimal_to_cents, parse_amount_to_cents


class MoneyAmountsTests(unittest.TestCase):
    def test_decimal_to_cents_rounds_half_up(self) -> None:
        self.assertEqual(decimal_to_cents(Decimal("10.125")), 1013)
        self.assertEqual(decimal_to_cents(Decimal("10.124")), 1012)

    def test_parse_amount_to_cents_accepts_int_and_decimal_string(self) -> None:
        self.assertEqual(parse_amount_to_cents(123), 123)
        self.assertEqual(parse_amount_to_cents("10.50"), 1050)

    def test_calcular_amount_percent_discount(self) -> None:
        result = calcular_amount(
            unit_price=10000,
            quantity=2,
            discount_type="percent",
            discount_value=15,
        )
        self.assertEqual(result["discount_amount"], 1500)
        self.assertEqual(result["final_unit_price"], 8500)
        self.assertEqual(result["line_total"], 17000)

    def test_calcular_amount_fixed_discount_with_clamp(self) -> None:
        result = calcular_amount(
            unit_price=500,
            quantity=3,
            discount_type="fixed",
            discount_value=900,
        )
        self.assertEqual(result["discount_amount"], 500)
        self.assertEqual(result["final_unit_price"], 0)
        self.assertEqual(result["line_total"], 0)

    def test_calcular_amount_rejects_negative_values(self) -> None:
        with self.assertRaises(ValueError):
            parse_amount_to_cents("-1")
        with self.assertRaises(ValueError):
            calcular_amount(unit_price=-1, quantity=1)


if __name__ == "__main__":
    unittest.main()

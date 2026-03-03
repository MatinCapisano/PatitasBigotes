import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.services.discount_s import get_applicable_discounts_for_product, is_discount_currently_valid


class DiscountsCategoryScopeTests(unittest.TestCase):
    def test_category_scope_matches_product_category_id(self) -> None:
        product = {
            "id": 10,
            "category_id": 3,
            "category": "Perros",
        }
        discounts = [
            {
                "id": 1,
                "name": "Category promo",
                "type": "percent",
                "value": 15,
                "scope": "category",
                "category_id": 3,
                "product_id": None,
                "is_active": True,
                "starts_at": None,
                "ends_at": None,
                "product_ids": [],
            }
        ]
        applicable = get_applicable_discounts_for_product(product=product, discounts=discounts)
        self.assertEqual(len(applicable), 1)
        self.assertEqual(applicable[0]["id"], 1)

    def test_category_scope_does_not_match_by_category_name(self) -> None:
        product = {
            "id": 10,
            "category_id": 4,
            "category": "Perros",
        }
        discounts = [
            {
                "id": 1,
                "name": "Category promo",
                "type": "percent",
                "value": 15,
                "scope": "category",
                "category_id": 3,
                "product_id": None,
                "is_active": True,
                "starts_at": None,
                "ends_at": None,
                "product_ids": [],
            }
        ]
        applicable = get_applicable_discounts_for_product(product=product, discounts=discounts)
        self.assertEqual(len(applicable), 0)

    def test_is_discount_currently_valid_handles_mixed_timezone_inputs(self) -> None:
        discount = {
            "id": 9,
            "name": "TZ promo",
            "type": "percent",
            "value": 10,
            "scope": "all",
            "category_id": None,
            "product_id": None,
            "is_active": True,
            "starts_at": "2026-01-01T00:00:00Z",
            "ends_at": datetime(2026, 12, 31, 23, 59, 59),  # naive on purpose
            "product_ids": [],
        }
        result = is_discount_currently_valid(
            discount=discount,
            at=datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()

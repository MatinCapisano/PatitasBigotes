import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.services.discount_s import get_applicable_discounts_for_product


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
                "scope_value": "3",
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
                "scope_value": "3",
                "is_active": True,
                "starts_at": None,
                "ends_at": None,
                "product_ids": [],
            }
        ]
        applicable = get_applicable_discounts_for_product(product=product, discounts=discounts)
        self.assertEqual(len(applicable), 0)


if __name__ == "__main__":
    unittest.main()

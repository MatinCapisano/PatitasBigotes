import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.db.models import Base, Category, Product, ProductVariant
from source.services import products_s


class ProductsMinVarPriceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine("sqlite:///:memory:")
        cls.TestSession = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )
        Base.metadata.create_all(bind=cls.engine)
        products_s.SessionLocal = cls.TestSession

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        session = self.TestSession()
        try:
            session.add_all([Category(name="cat"), Category(name="dog")])
            session.commit()
        finally:
            session.close()

    def test_create_product_without_price_and_without_variants(self) -> None:
        product = products_s.create_product(
            {
                "name": "Producto sin variantes",
                "description": "demo",
                "category": "cat",
                "active": True,
            }
        )
        self.assertIn("min_var_price", product)
        self.assertIsNone(product["min_var_price"])

    def test_get_product_returns_min_var_price_from_all_variants(self) -> None:
        session = self.TestSession()
        try:
            p = Product(name="P1", description=None, category_id=1)
            session.add(p)
            session.flush()
            session.add_all(
                [
                    ProductVariant(
                        product_id=p.id,
                        sku="P1-A",
                        size="S",
                        color="red",
                        price=1200.0,
                        stock=1,
                        is_active=True,
                    ),
                    ProductVariant(
                        product_id=p.id,
                        sku="P1-B",
                        size="M",
                        color="blue",
                        price=900.0,
                        stock=0,
                        is_active=False,
                    ),
                    ProductVariant(
                        product_id=p.id,
                        sku="P1-C",
                        size="L",
                        color="black",
                        price=1500.0,
                        stock=2,
                        is_active=True,
                    ),
                ]
            )
            session.commit()
            product_id = p.id
        finally:
            session.close()

        payload = products_s.get_product_by_id(product_id)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["min_var_price"], 900.0)

    def test_filter_by_min_price_uses_min_var_price(self) -> None:
        session = self.TestSession()
        try:
            p1 = Product(name="P1", description=None, category_id=1)
            p2 = Product(name="P2", description=None, category_id=1)
            session.add_all([p1, p2])
            session.flush()
            session.add_all(
                [
                    ProductVariant(
                        product_id=p1.id,
                        sku="P1-A",
                        size=None,
                        color=None,
                        price=500.0,
                        stock=1,
                        is_active=True,
                    ),
                    ProductVariant(
                        product_id=p2.id,
                        sku="P2-A",
                        size=None,
                        color=None,
                        price=1500.0,
                        stock=1,
                        is_active=True,
                    ),
                ]
            )
            session.commit()
        finally:
            session.close()

        data = products_s.filter_and_sort_products(min_price=1000)
        names = [product["name"] for product in data]
        self.assertEqual(names, ["P2"])

    def test_sort_by_price_orders_by_min_var_price(self) -> None:
        session = self.TestSession()
        try:
            p1 = Product(name="P1", description=None, category_id=1)
            p2 = Product(name="P2", description=None, category_id=1)
            session.add_all([p1, p2])
            session.flush()
            session.add_all(
                [
                    ProductVariant(
                        product_id=p1.id,
                        sku="P1-A",
                        size=None,
                        color=None,
                        price=2000.0,
                        stock=1,
                        is_active=True,
                    ),
                    ProductVariant(
                        product_id=p2.id,
                        sku="P2-A",
                        size=None,
                        color=None,
                        price=1000.0,
                        stock=1,
                        is_active=True,
                    ),
                ]
            )
            session.commit()
        finally:
            session.close()

        data = products_s.filter_and_sort_products(sort_by="price", sort_order="asc")
        names = [product["name"] for product in data if product["min_var_price"] is not None]
        self.assertEqual(names[:2], ["P2", "P1"])


if __name__ == "__main__":
    unittest.main()

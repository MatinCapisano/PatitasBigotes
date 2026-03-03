import os
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DB_PATH = BACKEND_DIR / "tmp" / "test_storefront_api.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")

from source.db.models import Base, Category, Product, ProductVariant
from source.db.session import SessionLocal, engine
from source.dependencies.auth_d import require_admin
from source.routes.products_r import router as products_router
from source.routes.storefront_r import storefront_product_detail, storefront_products


class StorefrontApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if DB_PATH.exists():
            DB_PATH.unlink()
        Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if DB_PATH.exists():
            DB_PATH.unlink()

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self._seed_catalog()

    def _seed_catalog(self) -> None:
        db = SessionLocal()
        try:
            cat_a = Category(name="Accesorios")
            cat_b = Category(name="Alimento")
            db.add_all([cat_a, cat_b])
            db.flush()

            p1 = Product(name="Collar A", description="d1", category_id=cat_a.id)
            p2 = Product(name="Correa B", description="d2", category_id=cat_a.id)
            p3 = Product(name="Comida C", description="d3", category_id=cat_b.id)
            db.add_all([p1, p2, p3])
            db.flush()

            db.add_all(
                [
                    ProductVariant(
                        product_id=p1.id,
                        sku="SKU-A1",
                        size="S",
                        color="Red",
                        price=10000,
                        stock=2,
                        is_active=True,
                    ),
                    ProductVariant(
                        product_id=p1.id,
                        sku="SKU-A2",
                        size="M",
                        color="Blue",
                        price=12000,
                        stock=0,
                        is_active=False,
                    ),
                    ProductVariant(
                        product_id=p2.id,
                        sku="SKU-B1",
                        size="U",
                        color="Black",
                        price=25000,
                        stock=0,
                        is_active=True,
                    ),
                    ProductVariant(
                        product_id=p3.id,
                        sku="SKU-C1",
                        size="L",
                        color="Green",
                        price=40000,
                        stock=5,
                        is_active=True,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

    def test_storefront_products_pagination_meta_is_consistent(self) -> None:
        db = SessionLocal()
        try:
            response = storefront_products(
                category_id=None,
                min_price=None,
                max_price=None,
                sort_by="created_at",
                sort_order="desc",
                limit=2,
                offset=0,
                db=db,
            )
        finally:
            db.close()

        self.assertIn("meta", response)
        meta = response["meta"]
        self.assertEqual(meta["limit"], 2)
        self.assertEqual(meta["offset"], 0)
        self.assertEqual(meta["total"], 3)
        self.assertTrue(meta["has_more"])
        self.assertEqual(len(response["data"]), 2)

    def test_storefront_products_filter_combination_category_and_price(self) -> None:
        db = SessionLocal()
        try:
            response = storefront_products(
                category_id=1,
                min_price=9000,
                max_price=20000,
                sort_by="price",
                sort_order="asc",
                limit=24,
                offset=0,
                db=db,
            )
        finally:
            db.close()

        ids = [item["id"] for item in response["data"]]
        self.assertEqual(ids, [1])

    def test_storefront_products_invalid_range_returns_400(self) -> None:
        db = SessionLocal()
        try:
            with self.assertRaises(HTTPException) as ctx:
                storefront_products(
                    category_id=None,
                    min_price=30000,
                    max_price=10000,
                    sort_by="price",
                    sort_order="asc",
                    limit=24,
                    offset=0,
                    db=db,
                )
        finally:
            db.close()
        self.assertEqual(ctx.exception.status_code, 400)

    def test_storefront_product_detail_returns_only_public_fields(self) -> None:
        db = SessionLocal()
        try:
            response = storefront_product_detail(product_id=1, db=db)
        finally:
            db.close()

        payload = response["data"]
        self.assertNotIn("stock", payload)
        self.assertNotIn("active", payload)
        self.assertIn("variants", payload)
        self.assertEqual(len(payload["variants"]), 1)
        variant_payload = payload["variants"][0]
        self.assertIn("in_stock", variant_payload)
        self.assertNotIn("stock", variant_payload)
        self.assertNotIn("sku", variant_payload)

    def test_storefront_product_detail_404_for_non_visible_product(self) -> None:
        db = SessionLocal()
        try:
            hidden_category = Category(name="Hidden")
            db.add(hidden_category)
            db.flush()
            hidden_product = Product(
                name="Hidden Product",
                description="hidden",
                category_id=hidden_category.id,
            )
            db.add(hidden_product)
            db.flush()
            db.add(
                ProductVariant(
                    product_id=hidden_product.id,
                    sku="SKU-HIDDEN-1",
                    size="U",
                    color="Gray",
                    price=9000,
                    stock=3,
                    is_active=False,
                )
            )
            db.commit()

            with self.assertRaises(HTTPException) as ctx:
                storefront_product_detail(product_id=int(hidden_product.id), db=db)
        finally:
            db.close()
        self.assertEqual(ctx.exception.status_code, 404)

    def test_admin_catalog_endpoints_still_require_admin(self) -> None:
        route_map: dict[tuple[str, str], APIRoute] = {}
        for route in products_router.routes:
            if isinstance(route, APIRoute):
                methods = sorted(route.methods or [])
                for method in methods:
                    route_map[(method, route.path)] = route

        products_get = route_map.get(("GET", "/products"))
        categories_get = route_map.get(("GET", "/categories"))

        self.assertIsNotNone(products_get)
        self.assertIsNotNone(categories_get)

        products_calls = {dependency.call for dependency in products_get.dependant.dependencies}
        categories_calls = {dependency.call for dependency in categories_get.dependant.dependencies}

        self.assertIn(require_admin, products_calls)
        self.assertIn(require_admin, categories_calls)


if __name__ == "__main__":
    unittest.main()

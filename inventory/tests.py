from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import Lot, Product, ProductCategory, StockMovement, Warehouse


class LotTrackingViewTests(TestCase):
    def setUp(self):
        self.category = ProductCategory.objects.create(name="Ham Madde")
        self.product = Product.objects.create(
            code="MAT-001",
            name="Kauçuk Taban",
            category=self.category,
            minimum_stock_level=Decimal("10"),
        )
        self.warehouse = Warehouse.objects.create(code="DEP-01", name="Ana Depo")
        self.lot = Lot.objects.create(
            product=self.product,
            lot_number="LOT-2026-001",
            initial_quantity=Decimal("50"),
            manufactured_date="2026-01-01",
            expiry_date="2026-12-31",
        )
        StockMovement.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot=self.lot,
            movement_type=StockMovement.MovementType.IN,
            quantity=Decimal("50"),
            reference_type="PurchaseOrder",
            reference_id=1,
            note="İlk giriş",
        )

    def test_lot_tracking_page_loads(self):
        response = self.client.get(reverse("inventory:lot_tracking_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LOT-2026-001")
        self.assertContains(response, "Lot Takibi")

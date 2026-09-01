from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from production.models import ProductionOrder, ProductionLine, Routing, BillOfMaterial
from quality.models import QualityCheck
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


class FireTrackingViewTests(TestCase):
    def setUp(self):
        self.category = ProductCategory.objects.create(name="Bitmiş Ürün")
        self.product = Product.objects.create(
            code="PRD-010",
            name="Spor Ayakkabı",
            category=self.category,
            minimum_stock_level=Decimal("20"),
        )
        self.warehouse = Warehouse.objects.create(code="DEP-02", name="Mamul Depo")
        self.line = ProductionLine.objects.create(code="LINE-01", name="Montaj Hattı")
        self.routing = Routing.objects.create(
            product=self.product,
            version=1,
            name="Standart Rota",
            description="Standart üretim",
        )
        self.bom = BillOfMaterial.objects.create(
            product=self.product,
            version=1,
            name="Standart Reçete",
            description="Standart reçete",
        )
        self.order = ProductionOrder.objects.create(
            order_number="PO-2026-001",
            product=self.product,
            bill_of_material=self.bom,
            routing=self.routing,
            production_line=self.line,
            planned_quantity=Decimal("100"),
            produced_quantity=Decimal("90"),
            scrapped_quantity=Decimal("10"),
            planned_start_date="2026-01-01T08:00:00Z",
            planned_end_date="2026-01-02T08:00:00Z",
            created_by=self._create_user(),
            raw_materials_warehouse=self.warehouse,
            finished_goods_warehouse=self.warehouse,
        )
        QualityCheck.objects.create(
            production_order=self.order,
            checked_quantity=Decimal("100"),
            accepted_quantity=Decimal("90"),
            rejected_quantity=Decimal("10"),
            scrapped_quantity=Decimal("10"),
            result=QualityCheck.Result.FAIL,
            rejection_reason="Yırtılma",
            notes="Ürün yüzeyinde kırılma",
        )

    def _create_user(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.create_user(username="planner1", email="planner@example.com", password="StrongPass123")

    def test_fire_tracking_page_loads(self):
        response = self.client.get(reverse("inventory:fire_tracking_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PO-2026-001")
        self.assertContains(response, "Fire Takibi")

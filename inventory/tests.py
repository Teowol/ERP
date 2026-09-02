from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from production.models import ProductionOrder, ProductionLine, Routing, BillOfMaterial
from distribution.tasks import _allocate_fifo_lots
from quality.models import QualityCheck
from inventory.admin import ProductAdmin
from inventory.models import Lot, Product, ProductCategory, Stock, StockMovement, Warehouse


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


class BarcodeIntegrationTests(TestCase):
    def setUp(self):
        self.category = ProductCategory.objects.create(name="Ham Madde")
        self.product = Product.objects.create(
            code="MAT-100",
            name="Kauçuk Taban",
            category=self.category,
            minimum_stock_level=Decimal("10"),
        )
        self.warehouse = Warehouse.objects.create(code="DEP-03", name="Ana Depo")
        Stock.objects.create(product=self.product, warehouse=self.warehouse, quantity=Decimal("0"))
        self.lot = Lot.objects.create(
            product=self.product,
            lot_number="LOT-2026-BAR-001",
            initial_quantity=Decimal("50"),
            manufactured_date="2026-01-01",
            expiry_date="2026-12-31",
        )

    def test_product_and_lot_have_unique_barcode_values(self):
        self.assertTrue(self.product.barcode)
        self.assertTrue(self.product.qr_code)
        self.assertTrue(self.lot.barcode)
        self.assertTrue(self.lot.qr_code)
        self.assertNotEqual(self.product.barcode, self.lot.barcode)
        self.assertIn("PRD-", self.product.barcode)
        self.assertIn("LOT-", self.lot.barcode)

    def test_duplicate_barcode_is_rejected(self):
        duplicate_product = Product(
            code="MAT-101",
            name="Yedek Kauçuk Taban",
            barcode=self.product.barcode,
            qr_code="ERP|PRODUCT|MAT-101|Yedek Kauçuk Taban|999",
        )
        with self.assertRaises(Exception):
            duplicate_product.full_clean()

    def test_barcode_search_can_find_product_and_lot(self):
        product_response = self.client.get(reverse("inventory:stock_level_list"), {"product": self.product.barcode})
        self.assertEqual(product_response.status_code, 200)
        self.assertContains(product_response, self.product.name)

        lot_response = self.client.get(reverse("inventory:lot_tracking_list"), {"product": self.lot.barcode})
        self.assertEqual(lot_response.status_code, 200)
        self.assertContains(lot_response, self.lot.lot_number)

    def test_qr_payload_omits_sensitive_values(self):
        payload = self.product.qr_payload
        self.assertIn("ERP|PRODUCT|", payload)
        self.assertNotIn("cost", payload.lower())
        self.assertNotIn("password", payload.lower())
        self.assertNotIn("secret", payload.lower())

    def test_duplicate_scan_reference_blocks_repeated_stock_movements(self):
        first = StockMovement.create_verified_movement(
            product=self.product,
            warehouse=self.warehouse,
            quantity=Decimal("10"),
            movement_type=StockMovement.MovementType.IN,
            lot=self.lot,
            reference_type="inventory_scan",
            reference_id=99,
            note="Tekar tarama",
            scan_reference="SCAN-INV-001",
        )
        second = StockMovement.create_verified_movement(
            product=self.product,
            warehouse=self.warehouse,
            quantity=Decimal("10"),
            movement_type=StockMovement.MovementType.IN,
            lot=self.lot,
            reference_type="inventory_scan",
            reference_id=99,
            note="Tekar tarama",
            scan_reference="SCAN-INV-001",
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(StockMovement.objects.filter(scan_reference="SCAN-INV-001").count(), 1)

    def test_existing_identifiers_are_immutable(self):
        self.product.barcode = "PRD-CHANGED"
        with self.assertRaises(Exception):
            self.product.save()

    def test_product_lot_mismatch_is_rejected(self):
        other = Product.objects.create(code="MAT-OTHER", name="Başka Malzeme")
        with self.assertRaisesRegex(ValueError, "ait değil"):
            StockMovement.create_verified_movement(
                product=other, warehouse=self.warehouse, lot=self.lot,
                quantity=Decimal("1"), movement_type=StockMovement.MovementType.OUT,
                scan_reference="SCAN-MISMATCH-001",
            )

    def test_insufficient_stock_does_not_create_movement(self):
        with self.assertRaisesRegex(ValueError, "Stok yetersiz"):
            StockMovement.create_verified_movement(
                product=self.product, warehouse=self.warehouse, lot=self.lot,
                quantity=Decimal("1"), movement_type=StockMovement.MovementType.OUT,
                scan_reference="SCAN-OUT-INSUFFICIENT",
            )
        self.assertFalse(StockMovement.objects.filter(scan_reference="SCAN-OUT-INSUFFICIENT").exists())

    def test_verified_scan_updates_stock_once(self):
        for _ in range(2):
            StockMovement.create_verified_movement(
                product=self.product, warehouse=self.warehouse, lot=self.lot,
                quantity=Decimal("5"), movement_type=StockMovement.MovementType.IN,
                scan_reference="SCAN-STOCK-ONCE",
            )
        stock = Stock.objects.get(product=self.product, warehouse=self.warehouse)
        self.assertEqual(stock.quantity, Decimal("5"))

    def test_admin_renders_barcode_and_qr_svg_previews(self):
        preview = ProductAdmin(Product, None).barcode_preview(self.product)
        self.assertIn("data:image/svg+xml;base64", preview)
        self.assertIn("alt=\"Barkod\"", preview)
        self.assertIn("alt=\"QR kod\"", preview)

    def test_fifo_allocation_uses_oldest_lot_first(self):
        newer_lot = Lot.objects.create(
            product=self.product, lot_number="LOT-2026-BAR-002",
            initial_quantity=Decimal("4"),
        )
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, lot=self.lot,
            movement_type=StockMovement.MovementType.IN, quantity=Decimal("3"),
        )
        StockMovement.objects.create(
            product=self.product, warehouse=self.warehouse, lot=newer_lot,
            movement_type=StockMovement.MovementType.IN, quantity=Decimal("4"),
        )
        allocations = _allocate_fifo_lots(self.product, self.warehouse, Decimal("5"))
        self.assertEqual([(lot.pk, qty) for lot, qty in allocations], [
            (self.lot.pk, Decimal("3")), (newer_lot.pk, Decimal("2")),
        ])

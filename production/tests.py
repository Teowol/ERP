from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventory.models import Product, ProductCategory, Stock, Warehouse
from production.models import (
    BillOfMaterial,
    BOMItem,
    ProductionCost,
    ProductionLine,
    ProductionOrder,
    Routing,
)


class ProductionCostCalculationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="costuser",
            email="cost@example.com",
            password="secret123",
        )
        self.category = ProductCategory.objects.create(name="Ham Madde")
        self.raw_material = Product.objects.create(
            code="RM-01",
            name="Yumuşak Deri",
            category=self.category,
            product_type=Product.ProductType.RAW_MATERIAL,
            unit=Product.Unit.KG,
        )
        self.finished_product = Product.objects.create(
            code="FG-01",
            name="Spor Ayakkabı",
            category=self.category,
            product_type=Product.ProductType.FINISHED_GOOD,
            unit=Product.Unit.PAIR,
        )
        self.raw_warehouse = Warehouse.objects.create(code="DEP-HM", name="Hammadde Deposu")
        self.finished_warehouse = Warehouse.objects.create(code="DEP-MM", name="Mamul Deposu")
        self.line = ProductionLine.objects.create(
            code="LINE-001",
            name="Üretim Hattı 1",
            capacity_per_day=Decimal("1000"),
        )
        self.bom = BillOfMaterial.objects.create(
            product=self.finished_product,
            name="BOM v1",
            status=BillOfMaterial.Status.ACTIVE,
            output_quantity=Decimal("1"),
            version=1,
        )
        self.bom_item = BOMItem.objects.create(
            bill_of_material=self.bom,
            component=self.raw_material,
            quantity=Decimal("2"),
            scrap_percentage=Decimal("10"),
        )
        self.routing = Routing.objects.create(
            product=self.finished_product,
            version=1,
            name="Rota v1",
            status=Routing.Status.ACTIVE,
        )
        Stock.objects.create(
            product=self.raw_material,
            warehouse=self.raw_warehouse,
            quantity=Decimal("100"),
            reserved_quantity=Decimal("0"),
        )
        self.order = ProductionOrder.objects.create(
            order_number="PO-1001",
            product=self.finished_product,
            bill_of_material=self.bom,
            routing=self.routing,
            production_line=self.line,
            planned_quantity=Decimal("10"),
            planned_start_date="2026-01-01T08:00:00Z",
            planned_end_date="2026-01-01T18:00:00Z",
            created_by=self.user,
            raw_materials_warehouse=self.raw_warehouse,
            finished_goods_warehouse=self.finished_warehouse,
            status=ProductionOrder.Status.IN_PROGRESS,
        )

    def test_calculates_cost_with_overrides_and_scrap(self):
        cost = ProductionCost.calculate_for_order(
            self.order,
            user=self.user,
            raw_material_cost_override=Decimal("25"),
            labor_cost_override=Decimal("50"),
            machine_cost_override=Decimal("20"),
            overhead_cost_override=Decimal("10"),
            scrap_quantity_override=Decimal("2"),
        )

        self.assertEqual(cost.production_order, self.order)
        self.assertEqual(cost.raw_material_cost, Decimal("25"))
        self.assertEqual(cost.scrap_cost, Decimal("21"))
        self.assertEqual(cost.total_cost, Decimal("126"))
        self.assertEqual(cost.unit_cost, Decimal("0"))
        self.assertTrue(cost.calculation_note)

    def test_zero_output_produces_safe_unit_cost(self):
        self.order.produced_quantity = Decimal("0")
        self.order.scrapped_quantity = Decimal("0")
        self.order.save(update_fields=["produced_quantity", "scrapped_quantity"])

        cost = ProductionCost.calculate_for_order(
            self.order,
            user=self.user,
            raw_material_cost_override=Decimal("30"),
            labor_cost_override=Decimal("10"),
        )

        self.assertEqual(cost.unit_cost, Decimal("0"))
        self.assertIn("sıfır", cost.calculation_note.lower())

    def test_repeated_calculation_updates_same_cost_record(self):
        first = ProductionCost.calculate_for_order(
            self.order,
            user=self.user,
            raw_material_cost_override=Decimal("20"),
        )
        second = ProductionCost.calculate_for_order(
            self.order,
            user=self.user,
            raw_material_cost_override=Decimal("30"),
            force=True,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.calculation_version, 2)
        self.assertEqual(second.raw_material_cost, Decimal("30"))

    def test_order_completion_creates_cost_record(self):
        self.order.complete_production(user=self.user)

        self.assertTrue(hasattr(self.order, "production_cost"))
        self.assertEqual(self.order.production_cost.production_order, self.order)

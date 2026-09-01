from django.contrib import admin, messages

from production.models import (
    BOMItem,
    BillOfMaterial,
    ProductionCost,
    ProductionLine,
    ProductionOrder,
    ProductionOrderComponent,
    ProductionOrderOperation,
    Routing,
    RoutingOperation,
    WorkCenter,
)


@admin.action(description="Seçili emirler için malzeme tüketimi kaydet")
def consume_materials_action(modeladmin, request, queryset):
    for order in queryset:
        try:
            order.consume_materials(user=request.user)
            modeladmin.message_user(
                request,
                f"{order.order_number} için malzeme tüketimi kaydedildi.",
                messages.SUCCESS,
            )
        except Exception as e:
            modeladmin.message_user(
                request,
                f"{order.order_number} hatası: {e}",
                messages.ERROR,
            )


@admin.action(description="Seçili emirleri tamamla (mamul girişi yap)")
def complete_production_action(modeladmin, request, queryset):
    for order in queryset:
        try:
            order.complete_production(user=request.user)
            modeladmin.message_user(
                request,
                f"{order.order_number} tamamlandı.",
                messages.SUCCESS,
            )
        except Exception as e:
            modeladmin.message_user(
                request,
                f"{order.order_number} hatası: {e}",
                messages.ERROR,
            )


class RoutingOperationInline(admin.TabularInline):
    model = RoutingOperation
    extra = 1


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 1


class ProductionOrderOperationInline(admin.TabularInline):
    model = ProductionOrderOperation
    extra = 0


class ProductionOrderComponentInline(admin.TabularInline):
    model = ProductionOrderComponent
    extra = 0


@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "capacity_per_day",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(WorkCenter)
class WorkCenterAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "production_line",
        "machine_name",
        "capacity_per_hour",
        "is_active",
    ]
    list_filter = ["production_line", "is_active"]
    search_fields = ["code", "name", "machine_name"]


@admin.register(Routing)
class RoutingAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "version",
        "name",
        "status",
        "valid_from",
        "valid_until",
    ]
    list_filter = ["status", "product"]
    search_fields = ["product__code", "product__name", "name"]
    inlines = [RoutingOperationInline]


@admin.register(RoutingOperation)
class RoutingOperationAdmin(admin.ModelAdmin):
    list_display = [
        "routing",
        "sequence",
        "name",
        "work_center",
        "setup_time_minutes",
        "cycle_time_minutes",
    ]
    list_filter = ["work_center"]
    search_fields = [
        "routing__product__code",
        "routing__product__name",
        "name",
    ]


@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "version",
        "name",
        "status",
        "output_quantity",
        "valid_from",
        "valid_until",
    ]
    list_filter = ["status", "product"]
    search_fields = ["product__code", "product__name", "name"]
    inlines = [BOMItemInline]


@admin.register(BOMItem)
class BOMItemAdmin(admin.ModelAdmin):
    list_display = [
        "bill_of_material",
        "component",
        "quantity",
        "scrap_percentage",
        "operation_sequence",
    ]
    list_filter = ["operation_sequence"]
    search_fields = [
        "bill_of_material__product__code",
        "component__code",
        "component__name",
    ]


@admin.register(ProductionCost)
class ProductionCostAdmin(admin.ModelAdmin):
    list_display = [
        "production_order",
        "product",
        "lot",
        "total_cost",
        "unit_cost",
        "raw_material_cost",
        "scrap_cost",
        "calculation_date",
    ]
    list_filter = ["product", "lot", "calculation_date"]
    search_fields = [
        "production_order__order_number",
        "product__code",
        "product__name",
        "lot__lot_number",
    ]
    readonly_fields = [
        "production_order",
        "product",
        "lot",
        "raw_material_cost",
        "labor_cost",
        "machine_cost",
        "overhead_cost",
        "scrap_cost",
        "total_cost",
        "produced_quantity",
        "scrap_quantity",
        "unit_cost",
        "calculation_date",
        "creation_source",
        "calculation_version",
        "calculation_note",
        "created_by",
        "created_at",
        "updated_at",
    ]


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "product",
        "production_line",
        "planned_quantity",
        "produced_quantity",
        "status",
        "priority",
        "planned_start_date",
        "raw_materials_warehouse",
        "finished_goods_warehouse",
        "reference_order_number",
    ]
    list_filter = ["status", "priority", "production_line"]
    search_fields = ["order_number", "product__name", "product__code", "reference_order_number"]
    inlines = [ProductionOrderOperationInline, ProductionOrderComponentInline]
    actions = [consume_materials_action, complete_production_action]
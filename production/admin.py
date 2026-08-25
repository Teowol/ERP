from django.contrib import admin

from production.models import (
    BOMItem,
    BillOfMaterial,
    ProductionLine,
    Routing,
    RoutingOperation,
    WorkCenter,
)


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


class RoutingOperationInline(admin.TabularInline):
    model = RoutingOperation
    extra = 1


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


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 1


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
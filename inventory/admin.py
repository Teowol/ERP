from django.contrib import admin

# Register your models here.

from django.contrib import admin

from inventory.models import (
    Lot,
    Product,
    ProductCategory,
    Stock,
    StockMovement,
    Warehouse,
)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "product_type",
        "category",
        "unit",
        "minimum_stock_level",
        "is_active",
    ]
    list_filter = ["product_type", "category", "is_active"]
    search_fields = ["code", "name"]


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    search_fields = ["code", "name"]


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "warehouse",
        "quantity",
        "reserved_quantity",
        "available_quantity",
        "updated_at",
    ]
    list_filter = ["warehouse"]
    search_fields = ["product__code", "product__name"]


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = [
        "lot_number",
        "product",
        "status",
        "initial_quantity",
        "remaining_quantity",
        "manufactured_date",
        "expiry_date",
        "created_at",
    ]
    list_filter = ["status", "product"]
    search_fields = ["lot_number", "product__code", "product__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "warehouse",
        "lot",
        "movement_type",
        "quantity",
        "reference_type",
        "reference_id",
        "created_at",
    ]
    list_filter = ["movement_type", "warehouse"]
    search_fields = ["product__code", "product__name", "lot__lot_number"]
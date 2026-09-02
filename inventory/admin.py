from django.contrib import admin

# Register your models here.

from django.contrib import admin

from inventory.barcodes import admin_code_preview
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
        "barcode",
        "qr_code",
        "product_type",
        "category",
        "unit",
        "minimum_stock_level",
        "is_active",
    ]
    list_filter = ["product_type", "category", "is_active"]
    search_fields = ["code", "name", "barcode", "qr_code"]
    readonly_fields = ["barcode_preview"]

    @admin.display(description="Barkod / QR Önizleme")
    def barcode_preview(self, obj):
        return admin_code_preview(obj)


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
    search_fields = ["product__code", "product__name", "product__barcode", "product__qr_code", "product__variant_details__sku"]


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = [
        "lot_number",
        "barcode",
        "qr_code",
        "product",
        "status",
        "initial_quantity",
        "remaining_quantity",
        "manufactured_date",
        "expiry_date",
        "created_at",
    ]
    list_filter = ["status", "product"]
    search_fields = ["lot_number", "barcode", "qr_code", "product__code", "product__name"]
    readonly_fields = ["created_at", "updated_at"] + ["barcode_preview"]

    @admin.display(description="Barkod / QR Önizleme")
    def barcode_preview(self, obj):
        return admin_code_preview(obj)


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
    search_fields = ["product__code", "product__name", "product__barcode", "product__qr_code", "product__variant_details__sku", "lot__lot_number", "lot__barcode", "lot__qr_code", "scan_reference"]

from django.contrib import admin

from procurement.models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestItem,
    Supplier,
    SupplierProduct,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "contact_person",
        "phone",
        "delivery_lead_time_days",
        "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "tax_number"]


@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = [
        "supplier",
        "product",
        "unit_price",
        "currency",
        "minimum_order_quantity",
        "is_preferred",
        "is_active",
    ]
    list_filter = ["currency", "is_preferred", "is_active", "supplier"]
    search_fields = [
        "supplier__name",
        "product__code",
        "product__name",
    ]


class PurchaseRequestItemInline(admin.TabularInline):
    model = PurchaseRequestItem
    extra = 1


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = [
        "request_number",
        "requested_by",
        "request_date",
        "required_date",
        "status",
    ]
    list_filter = ["status", "request_date"]
    search_fields = ["request_number"]
    inlines = [PurchaseRequestItemInline]


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "supplier",
        "order_date",
        "expected_delivery_date",
        "status",
        "currency",
        "total_amount",
    ]
    list_filter = ["status", "currency", "supplier"]
    search_fields = [
        "order_number",
        "supplier__code",
        "supplier__name",
    ]
    inlines = [PurchaseOrderItemInline]


class GoodsReceiptItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 1


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = [
        "receipt_number",
        "purchase_order",
        "received_date",
        "status",
        "delivered_by",
    ]
    list_filter = ["status", "received_date"]
    search_fields = [
        "receipt_number",
        "purchase_order__order_number",
    ]
    inlines = [GoodsReceiptItemInline]


@admin.register(PurchaseRequestItem)
class PurchaseRequestItemAdmin(admin.ModelAdmin):
    list_display = ["purchase_request", "product", "quantity"]
    search_fields = [
        "purchase_request__request_number",
        "product__code",
        "product__name",
    ]


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "purchase_order",
        "product",
        "quantity",
        "unit_price",
        "received_quantity",
    ]
    search_fields = [
        "purchase_order__order_number",
        "product__code",
        "product__name",
    ]


@admin.register(GoodsReceiptItem)
class GoodsReceiptItemAdmin(admin.ModelAdmin):
    list_display = [
        "goods_receipt",
        "product",
        "received_quantity",
        "accepted_quantity",
        "rejected_quantity",
        "lot_number",
        "warehouse",
    ]
    list_filter = ["warehouse"]
    search_fields = [
        "goods_receipt__receipt_number",
        "product__code",
        "product__name",
        "lot_number",
    ]
from django.contrib import admin

from .models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "company_name",
        "contact_name",
        "phone",
        "email",
        "payment_term_days",
        "is_active",
    ]
    list_filter = ["is_active", "country", "currency"]
    search_fields = [
        "code",
        "company_name",
        "commercial_title",
        "contact_name",
        "tax_number",
        "email",
        "phone",
    ]
    ordering = ["code"]


class PurchaseRequestLineInline(admin.TabularInline):
    model = PurchaseRequestLine
    extra = 1
    autocomplete_fields = ["product"]


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = [
        "request_number",
        "source",
        "status",
        "requested_by",
        "required_date",
        "requested_at",
        "approved_by",
    ]
    list_filter = ["status", "source", "requested_at"]
    search_fields = [
        "request_number",
        "purpose",
        "requested_by__username",
    ]
    autocomplete_fields = ["requested_by", "approved_by"]
    readonly_fields = ["requested_at", "approved_at", "created_at", "updated_at"]
    inlines = [PurchaseRequestLineInline]
    ordering = ["-created_at"]


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 1
    autocomplete_fields = ["product"]
    readonly_fields = ["line_total"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "supplier",
        "status",
        "order_date",
        "expected_delivery_date",
        "currency",
        "created_by",
    ]
    list_filter = ["status", "currency", "order_date", "supplier"]
    search_fields = [
        "order_number",
        "supplier__code",
        "supplier__company_name",
        "purchase_request__request_number",
    ]
    autocomplete_fields = [
        "purchase_request",
        "supplier",
        "created_by",
    ]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PurchaseOrderLineInline]
    ordering = ["-order_date", "-id"]


@admin.register(PurchaseRequestLine)
class PurchaseRequestLineAdmin(admin.ModelAdmin):
    list_display = [
        "purchase_request",
        "product",
        "requested_quantity",
        "note",
    ]
    list_filter = ["purchase_request__status"]
    search_fields = [
        "purchase_request__request_number",
        "product__code",
        "product__name",
    ]
    autocomplete_fields = ["purchase_request", "product"]


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = [
        "purchase_order",
        "product",
        "ordered_quantity",
        "received_quantity",
        "unit_price",
        "line_total",
    ]
    list_filter = ["purchase_order__status"]
    search_fields = [
        "purchase_order__order_number",
        "product__code",
        "product__name",
    ]
    autocomplete_fields = ["purchase_order", "product"]
    readonly_fields = ["line_total"]
from django.contrib import admin

from distribution.models import Customer, SalesOrder, SalesOrderLine


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 1
    fields = ["product", "quantity", "unit_price", "line_total", "produced_quantity", "shipped_quantity"]
    readonly_fields = ["line_total"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "tax_number", "email", "phone", "is_active"]
    search_fields = ["code", "name", "tax_number"]


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "customer",
        "status",
        "requested_delivery_date",
        "promised_delivery_date",
        "total_amount",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["order_number", "customer__name", "customer__code"]
    inlines = [SalesOrderLineInline]

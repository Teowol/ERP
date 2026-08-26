from django.contrib import admin

from .models import QualityCheck


@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = [
        "production_order",
        "check_date",
        "checked_quantity",
        "accepted_quantity",
        "rejected_quantity",
        "scrapped_quantity",
        "result",
        "checked_by",
    ]
    list_filter = ["result", "check_date"]
    search_fields = ["production_order__order_number", "notes"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "check_date"

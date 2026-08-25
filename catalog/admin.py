from django.contrib import admin
from catalog.models import ShoeModel, Color, Size, ProductVariant


@admin.register(ShoeModel)
class ShoeModelAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "target_gender", "is_active", "created_at"]
    list_filter = ["target_gender", "is_active"]
    search_fields = ["code", "name"]


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "hex_code"]
    search_fields = ["code", "name"]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["size_value", "description"]
    search_fields = ["size_value"]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["sku", "shoe_model", "color", "size", "product", "is_active"]
    list_filter = ["shoe_model", "color", "size", "is_active"]
    search_fields = ["sku", "shoe_model__name", "product__code"]
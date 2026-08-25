from django.db import models
from inventory.models import Product

class ShoeModel(models.Model):
    """Spor ayakkabı ana model tanımı (Örn: Pegasus Pro, Air Runner)."""

    code = models.CharField(max_length=50, unique=True, verbose_name="Model Kodu")
    name = models.CharField(max_length=150, verbose_name="Model Adı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    target_gender = models.CharField(
        max_length=20,
        choices=[
            ("men", "Erkek"),
            ("women", "Kadın"),
            ("unisex", "Unisex"),
            ("kids", "Çocuk"),
        ],
        default="unisex",
        verbose_name="Hedef Kitle",
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        ordering = ["code"]
        verbose_name = "Ayakkabı Modeli"
        verbose_name_plural = "Ayakkabı Modelleri"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Color(models.Model):
    """Renk tanımları (Örn: Gece Siyahı, Neon Sarı)."""

    code = models.CharField(max_length=30, unique=True, verbose_name="Renk Kodu")
    name = models.CharField(max_length=50, verbose_name="Renk Adı")
    hex_code = models.CharField(
        max_length=7,
        blank=True,
        help_text="Örn: #000000",
        verbose_name="HEX Kodu",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Renk"
        verbose_name_plural = "Renkler"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Size(models.Model):
    """Numara/Beden tanımları (Örn: 40, 41, 42.5)."""

    size_value = models.CharField(max_length=10, unique=True, verbose_name="Numara")
    description = models.CharField(max_length=50, blank=True, verbose_name="Açıklama")

    class Meta:
        ordering = ["size_value"]
        verbose_name = "Numara"
        verbose_name_plural = "Numaralar"

    def __str__(self):
        return self.size_value


class ProductVariant(models.Model):
    """Model, Renk ve Beden kombinasyonu ile oluşan nihai satış/üretim varyantı."""

    sku = models.CharField(max_length=100, unique=True, verbose_name="SKU / Barkod")
    shoe_model = models.ForeignKey(
        ShoeModel,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="Ayakkabı Modeli",
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        related_name="variants",
        verbose_name="Renk",
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        related_name="variants",
        verbose_name="Numara",
    )
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="variant_details",
        verbose_name="İlişkili Envanter Ürünü",
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shoe_model", "color", "size"],
                name="unique_shoe_color_size_combination",
            )
        ]
        ordering = ["shoe_model", "color", "size"]
        verbose_name = "Ürün Varyantı"
        verbose_name_plural = "Ürün Varyantları"

    def __str__(self):
        return f"{self.sku} | {self.shoe_model.name} - {self.color.name} - {self.size.size_value}"
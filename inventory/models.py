import re
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q


class ProductCategory(models.Model):
    """Ürün kategorileri. Örneğin: Ham Madde, Yarı Mamul, Bitmiş Ürün."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Ürün Kategorisi"
        verbose_name_plural = "Ürün Kategorileri"

    def __str__(self):
        return self.name


class Product(models.Model):
    """Spor ayakkabı üretiminde kullanılan tüm maddeler."""

    class ProductType(models.TextChoices):
        RAW_MATERIAL = "raw_material", "Ham Madde"
        SEMI_FINISHED = "semi_finished", "Yarı Mamul"
        FINISHED_GOOD = "finished_good", "Bitmiş Ürün"
        PACKAGING = "packaging", "Ambalaj"
        CONSUMABLE = "consumable", "Sarf Malzemesi"

    class Unit(models.TextChoices):
        PIECE = "piece", "Adet"
        KG = "kg", "Kilogram"
        METER = "meter", "Metre"
        SQUARE_METER = "m2", "Metrekare"
        PAIR = "pair", "Çift"
        LITER = "liter", "Litre"
        ROLL = "roll", "Rulo"

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    barcode = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="Barkod",
        help_text="Ürün için tekil barkod değeri. Mevcut değer değişmez; yeniden oluşturulmaz.",
    )
    qr_code = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="QR Kodu",
        help_text="Ürün için tekil QR kod metni. Hassas bilgi içermez.",
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
    )
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.RAW_MATERIAL,
    )
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.KG,
    )
    minimum_stock_level = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"

    @staticmethod
    def _normalize_scan_code(value):
        if value is None:
            return ""
        normalized = value.strip().upper()
        if not normalized:
            return ""
        if not re.fullmatch(r"[A-Z0-9\-]+", normalized):
            raise ValidationError("Barkod/QR değeri sadece harf, rakam ve tire içerebilir.")
        return normalized

    def _generate_barcode(self):
        base = re.sub(r"[^A-Z0-9-]", "", (self.code or self.name or f"ITEM-{self.pk or 'NEW'}").upper())
        return f"PRD-{base[:40]}-{uuid.uuid4().hex[:6].upper()}"

    @property
    def qr_payload(self):
        safe_name = (self.name or self.code or "product").replace("|", "-")
        return f"ERP|PRODUCT|{self.code}|{safe_name}|{self.barcode or self._generate_barcode()}"

    def clean(self):
        super().clean()
        if self.barcode:
            self.barcode = self._normalize_scan_code(self.barcode)
        if not self.barcode:
            self.barcode = self._generate_barcode()
        if self.qr_code:
            self.qr_code = self.qr_code.strip()
            bad_words = ["cost", "price", "password", "secret", "token", "api_key", "sifre", "maliyet", "şifre"]
            if any(word in self.qr_code.lower() for word in bad_words):
                raise ValidationError({"qr_code": "QR kodunda maliyet, şifre veya hassas bilgi tutulmamalıdır."})
        if not self.qr_code:
            self.qr_code = self.qr_payload

        if Product.objects.filter(barcode=self.barcode).exclude(pk=self.pk).exists():
            raise ValidationError({"barcode": "Bu barkod başka bir ürünle eşleşiyor."})
        if Product.objects.filter(qr_code=self.qr_code).exclude(pk=self.pk).exists():
            raise ValidationError({"qr_code": "Bu QR kodu başka bir ürünle eşleşiyor."})
        if Lot.objects.filter(barcode=self.barcode).exists():
            raise ValidationError({"barcode": "Bu barkod bir lot tarafından kullanılıyor."})
        if Lot.objects.filter(qr_code=self.qr_code).exists():
            raise ValidationError({"qr_code": "Bu QR kodu bir lot tarafından kullanılıyor."})

    def save(self, *args, **kwargs):
        if self.pk:
            original = Product.objects.filter(pk=self.pk).values("barcode", "qr_code").first()
            if original and (
                original["barcode"] != self.barcode or original["qr_code"] != self.qr_code
            ):
                raise ValidationError("Mevcut ürün barkodu ve QR kodu değiştirilemez.")
        self.clean()
        return super().save(*args, **kwargs)

    @classmethod
    def resolve_by_identifier(cls, value):
        normalized = (value or "").strip()
        if not normalized:
            return None
        return (
            cls.objects.filter(Q(barcode__iexact=normalized) | Q(qr_code=normalized) | Q(code__iexact=normalized) | Q(variant_details__sku__iexact=normalized))
            .order_by("pk")
            .first()
        )

    def __str__(self):
        return f"{self.code} - {self.name}"


class Warehouse(models.Model):
    """Depolar. Örneğin: Ham Madde Deposu, Yarı Mamul Deposu, Mamul Deposu."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Depo"
        verbose_name_plural = "Depolar"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Lot(models.Model):
    """Ürün lot / parti takibi. Üretimden çıkan veya satın alınan her parti
    için benzersiz bir lot numarası tutulur."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktif"
        QUARANTINED = "quarantined", "Karantinada"
        CONSUMED = "consumed", "Tükendi"
        EXPIRED = "expired", "Süresi Doldu"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="lots",
        verbose_name="Ürün",
    )
    lot_number = models.CharField(
        max_length=60,
        unique=True,
        verbose_name="Lot Numarası",
    )
    barcode = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="Lot Barkodu",
        help_text="Lot için tekil barkod değeri. Mevcut değer değişmez.",
    )
    qr_code = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="Lot QR Kodu",
        help_text="Lot için tekil QR kod metni. Hassas bilgi içermez.",
    )
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Lotun oluştuğu kayıt türü. Örneğin: ProductionOrder, PurchaseOrder.",
        verbose_name="Referans Türü",
    )
    reference_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name="Referans ID",
    )
    manufactured_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Üretim Tarihi",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Son Kullanma Tarihi",
    )
    initial_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Başlangıç Miktarı",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Durum",
    )
    note = models.TextField(blank=True, verbose_name="Not")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lot"
        verbose_name_plural = "Lotlar"

    @staticmethod
    def _normalize_scan_code(value):
        if value is None:
            return ""
        normalized = value.strip().upper()
        if not normalized:
            return ""
        if not re.fullmatch(r"[A-Z0-9\-]+", normalized):
            raise ValidationError("Lot barkodu/QR değeri sadece harf, rakam ve tire içerebilir.")
        return normalized

    def _generate_barcode(self):
        base = re.sub(r"[^A-Z0-9-]", "", (self.product.code or self.lot_number or f"LOT-{self.pk or 'NEW'}").upper())
        return f"LOT-{base[:40]}-{uuid.uuid4().hex[:6].upper()}"

    @property
    def qr_payload(self):
        safe_lot = (self.lot_number or self.product.code or "lot").replace("|", "-")
        return f"ERP|LOT|{self.product.code}|{safe_lot}|{self.barcode or self._generate_barcode()}"

    def clean(self):
        super().clean()
        if self.barcode:
            self.barcode = self._normalize_scan_code(self.barcode)
        if not self.barcode:
            self.barcode = self._generate_barcode()
        if self.qr_code:
            self.qr_code = self.qr_code.strip()
            bad_words = ["cost", "price", "password", "secret", "token", "api_key", "sifre", "maliyet", "şifre"]
            if any(word in self.qr_code.lower() for word in bad_words):
                raise ValidationError({"qr_code": "QR kodunda maliyet, şifre veya hassas bilgi tutulmamalıdır."})
        if not self.qr_code:
            self.qr_code = self.qr_payload

        if Lot.objects.filter(barcode=self.barcode).exclude(pk=self.pk).exists():
            raise ValidationError({"barcode": "Bu lot barkodu başka bir lot ile eşleşiyor."})
        if Lot.objects.filter(qr_code=self.qr_code).exclude(pk=self.pk).exists():
            raise ValidationError({"qr_code": "Bu lot QR kodu başka bir lot ile eşleşiyor."})
        if Product.objects.filter(barcode=self.barcode).exists():
            raise ValidationError({"barcode": "Bu barkod bir ürün tarafından kullanılıyor."})
        if Product.objects.filter(qr_code=self.qr_code).exists():
            raise ValidationError({"qr_code": "Bu QR kodu bir ürün tarafından kullanılıyor."})

    def save(self, *args, **kwargs):
        if self.pk:
            original = Lot.objects.filter(pk=self.pk).values("barcode", "qr_code").first()
            if original and (
                original["barcode"] != self.barcode or original["qr_code"] != self.qr_code
            ):
                raise ValidationError("Mevcut lot barkodu ve QR kodu değiştirilemez.")
        self.clean()
        return super().save(*args, **kwargs)

    @property
    def remaining_quantity(self):
        """Bu lottan hâlâ stokta kalan net miktar (giriş - çıkış)."""
        in_qty = self.stock_movements.filter(
            movement_type=StockMovement.MovementType.IN
        ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0")
        out_qty = self.stock_movements.filter(
            movement_type=StockMovement.MovementType.OUT
        ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0")
        return in_qty - out_qty

    @classmethod
    def resolve_by_identifier(cls, value):
        normalized = (value or "").strip()
        if not normalized:
            return None
        return (
            cls.objects.filter(Q(barcode__iexact=normalized) | Q(qr_code=normalized) | Q(lot_number__iexact=normalized))
            .order_by("pk")
            .first()
        )

    def __str__(self):
        return f"{self.lot_number} ({self.product.code})"


class Stock(models.Model):
    """Ürünün depodaki mevcut, ayrılmış ve kullanılabilir miktarı."""

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stocks",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    reserved_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse_stock",
            ),
        ]
        ordering = ["product", "warehouse"]
        verbose_name = "Stok"
        verbose_name_plural = "Stoklar"

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.product} - {self.warehouse}"


class StockMovement(models.Model):
    """Stok hareketleri. Giriş, çıkış, düzeltme, depolar arası transfer."""

    class MovementType(models.TextChoices):
        IN = "in", "Giriş"
        OUT = "out", "Çıkış"
        ADJUSTMENT = "adjustment", "Düzeltme"
        TRANSFER = "transfer", "Transfer"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    lot = models.ForeignKey(
        "Lot",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        null=True,
        blank=True,
        verbose_name="Lot",
        help_text="Bu hareketin ilişkili olduğu lot (varsa).",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="İlişkili olduğu kayıt türü. Örneğin: PurchaseOrder, ProductionOrder, Shipment.",
    )
    reference_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="İlişkili kaydın ID'si.",
    )
    scan_reference = models.CharField(
        max_length=128,
        blank=True,
        unique=True,
        db_index=True,
        null=True,
        verbose_name="Tarama Referansı",
        help_text="Aynı barkod/QR okutması tekrar stok hareketi oluşturmasın diye tekil referans.",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stok Hareketi"
        verbose_name_plural = "Stok Hareketleri"

    @classmethod
    def create_verified_movement(
        cls, *, product, warehouse, quantity, movement_type, lot=None,
        reference_type="", reference_id=None, note="", scan_reference=None,
    ):
        if not product or not warehouse:
            raise ValueError("Ürün ve depo zorunludur.")
        quantity = Decimal(str(quantity))
        if quantity <= Decimal("0"):
            raise ValueError("Hareket miktarı sıfırdan büyük olmalıdır.")
        if movement_type not in (cls.MovementType.IN, cls.MovementType.OUT):
            raise ValueError("Okutmalı işlem yalnızca stok giriş veya çıkışı olabilir.")
        if lot and lot.product_id != product.pk:
            raise ValueError("Okutulan lot seçilen ürüne ait değil.")
        scan_reference = (scan_reference or "").strip()
        if not scan_reference or len(scan_reference) > 128:
            raise ValueError("Tarama referansı zorunludur ve 128 karakteri aşamaz.")

        with transaction.atomic():
            stock, _ = Stock.objects.select_for_update().get_or_create(
                product=product, warehouse=warehouse,
                defaults={"quantity": Decimal("0"), "reserved_quantity": Decimal("0")},
            )
            existing = cls.objects.select_for_update().filter(
                scan_reference=scan_reference
            ).first()
            if existing:
                return existing
            if movement_type == cls.MovementType.OUT:
                if stock.available_quantity < quantity:
                    raise ValueError(
                        f"Stok yetersiz: kullanılabilir {stock.available_quantity}, istenen {quantity}."
                    )
                if lot:
                    incoming = cls.objects.filter(
                        lot=lot, warehouse=warehouse, movement_type=cls.MovementType.IN
                    ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0")
                    outgoing = cls.objects.filter(
                        lot=lot, warehouse=warehouse, movement_type=cls.MovementType.OUT
                    ).aggregate(total=models.Sum("quantity"))["total"] or Decimal("0")
                    if incoming - outgoing < quantity:
                        raise ValueError("Okutulan lotta yeterli stok yok.")
            movement = cls.objects.create(
                product=product, warehouse=warehouse, lot=lot,
                movement_type=movement_type, quantity=quantity,
                reference_type=reference_type, reference_id=reference_id,
                note=note, scan_reference=scan_reference,
            )
            stock.quantity += quantity if movement_type == cls.MovementType.IN else -quantity
            stock.save(update_fields=["quantity", "updated_at"])
            return movement

    def __str__(self):
        return f"{self.product} - {self.movement_type} - {self.quantity}"

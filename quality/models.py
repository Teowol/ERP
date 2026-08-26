from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


class QualityCheck(models.Model):
    """Üretim emrine bağlı kalite kontrol kaydı."""

    class Result(models.TextChoices):
        PASS = "pass", "Kabul (Geçti)"
        PARTIAL = "partial", "Kısmi Kabul"
        FAIL = "fail", "Red"

    production_order = models.ForeignKey(
        "production.ProductionOrder",
        on_delete=models.CASCADE,
        related_name="quality_checks",
        verbose_name="Üretim Emri",
    )
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_checks",
        verbose_name="Kontrol Eden",
    )
    check_date = models.DateTimeField(default=timezone.now, verbose_name="Kontrol Tarihi")
    checked_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Kontrol Edilen Miktar",
    )
    accepted_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Kabul Edilen Miktar",
    )
    rejected_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Reddedilen Miktar",
    )
    scrapped_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="Fire Miktarı",
    )
    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.PASS,
        verbose_name="Sonuç",
    )
    rejection_reason = models.TextField(blank=True, verbose_name="Red / Fire Nedeni")
    notes = models.TextField(blank=True, verbose_name="Kontrol Notları")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-check_date"]
        verbose_name = "Kalite Kontrol Kaydı"
        verbose_name_plural = "Kalite Kontrol Kayıtları"

    def __str__(self):
        return f"{self.production_order.order_number} - {self.get_result_display()} ({self.check_date:%d.%m.%Y})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.accepted_quantity + self.rejected_quantity > self.checked_quantity:
            raise ValidationError(
                "Kabul + red miktarı, kontrol edilen miktardan fazla olamaz."
            )
        if self.scrapped_quantity > self.rejected_quantity:
            raise ValidationError(
                "Fire miktarı, reddedilen miktardan fazla olamaz."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

# cart/models.py
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.urls import reverse

from decimal import Decimal
from django.db.models import F, Sum, ExpressionWrapper, DecimalField


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT         = "DRAFT", "Nháp"
        PENDING_ADMIN = "PENDING_ADMIN", "Chờ admin xác nhận"
        CONFIRMED     = "CONFIRMED", "Đã xác nhận"
        CANCELLED     = "CANCELLED", "Đã hủy"

    # Chủ đơn hàng (KH mua) — tránh đụng với shop.Order bằng related_name riêng
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_orders",
    )

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Thông tin xác nhận (admin)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="orders_confirmed",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    # Thông tin hủy (admin)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="orders_cancelled",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "created_at")),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk} - {self.get_status_display()}"

    def get_absolute_url(self):
        return reverse("cart:order_detail", args=(self.pk,))

    @property
    def total_price(self) -> Decimal:
        """
        Tổng tiền tính trực tiếp trong DB: SUM(price * quantity).
        Không phụ thuộc vào property/method line_total của OrderItem.
        """
        amount = self.items.aggregate(
            s=Sum(
                ExpressionWrapper(
                    F("price") * F("quantity"),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
        )["s"]
        return amount if amount is not None else Decimal("0")

    # ===== Hành động nghiệp vụ =====
    def confirm(self, by_user):
        """Admin xác nhận đơn."""
        self.status = self.Status.CONFIRMED
        self.confirmed_by = by_user
        self.confirmed_at = timezone.now()
        # clear thông tin hủy nếu có
        self.cancelled_by = None
        self.cancelled_at = None
        self.cancel_reason = ""
        self.save(update_fields=[
            "status", "confirmed_by", "confirmed_at",
            "cancelled_by", "cancelled_at", "cancel_reason",
        ])

    def cancel(self, by_user, reason: str = ""):
        """Admin hủy đơn (lưu người & thời gian hủy, lý do)."""
        self.status = self.Status.CANCELLED
        self.cancelled_by = by_user
        self.cancelled_at = timezone.now()
        self.cancel_reason = reason or ""
        self.save(update_fields=["status", "cancelled_by", "cancelled_at", "cancel_reason"])


# cart/models.py (cập nhật OrderItem)
class OrderItem(models.Model):
    order = models.ForeignKey("cart.Order", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("shop.Product", on_delete=models.PROTECT)
    plan = models.ForeignKey("shop.ServicePlan", null=True, blank=True, on_delete=models.PROTECT)  # NEW
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        """Tổng dòng = đơn giá * số lượng (luôn trả về Decimal)."""
        p = self.price or Decimal("0")
        q = int(self.quantity or 0)
        return p * q
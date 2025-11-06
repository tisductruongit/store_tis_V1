# shop/models.py (rewritten)
from __future__ import annotations
from decimal import Decimal
import re
import unicodedata
from typing import Optional

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator


# ===================== Helpers =====================

def _slugify_vn(text: str) -> str:
    """
    Chuyển tiếng Việt -> slug ascii: 'Gói dịch vụ 1' -> 'goi-dich-vu-1'
    """
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    return (text.strip("-").lower()) or "item"


def _unique_slug(model: type[models.Model], base: str, instance: models.Model, slug_field: str = "slug") -> str:
    """Đảm bảo slug không trùng trong model cho instance hiện tại."""
    slug = base
    i = 1
    qs = model._default_manager.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(**{slug_field: slug}).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def product_image_upload_to(instance: "ProductImage", filename: str) -> str:
    return f"products/{instance.product_id}/{filename}"

# --- legacy compat for old migrations ---
# Một số migration cũ (0001_initial.py) import trực tiếp các hàm dưới đây
# như shop.models.product_main_image_path và product_extra_image_path.
# Ta giữ shim để đảm bảo load migration không lỗi.

def product_main_image_path(instance, filename):
    """Đường dẫn ảnh chính cho Product.image (giữ tương thích migration cũ)."""
    return f"products/main/{filename}"


def product_extra_image_path(instance, filename):
    """Đường dẫn ảnh phụ cho ProductImage (giữ tương thích migration cũ)."""
    # Nếu migration cũ mong muốn cấu trúc khác, bạn có thể điều chỉnh; mặc định dùng product_id
    try:
        pid = getattr(instance, "product_id", None) or instance.product.pk
    except Exception:
        pid = "extra"
    return f"products/{pid}/{filename}"


# ===================== Category =====================
class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordering", "name"]
        indexes = [models.Index(fields=["is_active", "ordering"]) ]
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        base = _slugify_vn(self.slug or self.name)
        self.slug = _unique_slug(Category, base, self)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shop:category_detail", kwargs={"slug": self.slug})


# ===================== Product =====================
class Product(models.Model):
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=210, unique=True, blank=True)
    sku = models.CharField(max_length=64, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    supplier = models.CharField(max_length=150, blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/main/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "created_at"]),
            models.Index(fields=["category", "is_active"]),
        ]
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"

    def __str__(self) -> str:
        return self.name

    @property
    def unit_price(self) -> Decimal:
        return self.sale_price if (self.sale_price is not None and self.sale_price >= 0) else self.price

    def save(self, *args, **kwargs):
        base = _slugify_vn(self.slug or self.name)
        self.slug = _unique_slug(Product, base, self)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shop:product_detail", kwargs={"slug": self.slug})


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to=product_image_upload_to)
    alt = models.CharField(max_length=200, blank=True)
    ordering = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordering", "id"]
        indexes = [models.Index(fields=["product", "ordering"]) ]
        verbose_name = "Ảnh sản phẩm"
        verbose_name_plural = "Ảnh sản phẩm"

    def __str__(self) -> str:
        return f"{self.product.name} (#{self.pk})"


# ===================== Consultation Request =====================
class ConsultationRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Mới"
        CONTACTED = "contacted", "Đã liên hệ"
        DONE = "done", "Hoàn tất"
        CANCELLED = "cancelled", "Đã hủy"

    # Người gửi yêu cầu có thể là khách vãng lai
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="consult_requests")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="consult_requests")
    customer_name = models.CharField(max_length=150, blank=True)
    customer_phone = models.CharField(max_length=30, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="consult_handled")
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]) ,
            models.Index(fields=["product", "status"]) ,
        ]
        verbose_name = "Yêu cầu tư vấn"
        verbose_name_plural = "Yêu cầu tư vấn"

    def __str__(self) -> str:
        who = self.user.username if self.user_id else (self.customer_name or "Khách")
        return f"{who} — {self.product.name}"

from django.utils import timezone
# ===================== Orders =====================
class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Nháp"
        PENDING = "pending", "Chờ thanh toán"
        PAID = "paid", "Đã thanh toán"
        CANCELLED = "cancelled", "Đã hủy"
        REFUNDED = "refunded", "Hoàn tiền"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    note = models.TextField(blank=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))  # tổng cache
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]) ,
            models.Index(fields=["user", "-created_at"]) ,
        ]
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Đơn hàng"

    def __str__(self) -> str:
        return f"Order #{self.pk}"

    def recalc_total(self) -> Decimal:
        total = (
            self.items.aggregate(s=models.Sum(models.F("quantity") * models.F("price")))
            .get("s") or Decimal("0")
        )
        self.total = total
        return total

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # đảm bảo tổng luôn đúng khi đã có items
        if self.pk:
            self.recalc_total()
            super().save(update_fields=["total"])

    def activate_subscriptions(self, started_at=None):
        """Tạo Subscription cho các dòng hàng có gói khi đơn đã xác nhận."""
        if not self.user_id:
            return 0
        started_at = started_at or timezone.now()
        created = 0
        for item in self.items.select_related("plan", "product"):
            if not item.plan_id:
                continue
            sub = Subscription.objects.create(
                user=self.user,
                product=item.product,
                plan=item.plan,
                started_at=started_at,   # bắt đầu từ lúc admin xác nhận
                status=Subscription.Status.ACTIVE,
            )
            # ends_at sẽ tự tính trong Subscription.save()
            created += 1
        return created



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])  # đơn giá tại thời điểm đặt
    created_at = models.DateTimeField(auto_now_add=True)
    plan = models.ForeignKey("ServicePlan", null=True, blank=True,
                             on_delete=models.PROTECT, related_name="order_items")
    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["order"]) ]
        verbose_name = "Mục đơn hàng"
        verbose_name_plural = "Mục đơn hàng"

    def __str__(self) -> str:
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self) -> Decimal:
        return (self.price or Decimal("0")) * self.quantity


# ===================== Page Views (analytics đơn giản) =====================
class PageView(models.Model):
    path = models.CharField(max_length=300)
    referer = models.CharField(max_length=300, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="pageviews")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]) ,
            models.Index(fields=["path"]) ,
        ]
        verbose_name = "Lượt xem trang"
        verbose_name_plural = "Lượt xem trang"

    def __str__(self) -> str:
        return f"{self.path} @ {self.created_at:%Y-%m-%d %H:%M}"


# ===================== Service Plans & Subscriptions =====================
class ServicePlan(models.Model):
    class Term(models.TextChoices):
        MONTH = "month", "Theo tháng (30 ngày)"
        QUARTER = "quarter", "Theo quý (90 ngày)"
        YEAR = "year", "Theo năm (365 ngày)"
        CUSTOM = "custom", "Tùy chỉnh (custom_days)"

    product = models.ForeignKey("Product", related_name="plans", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    term = models.CharField(max_length=12, choices=Term.choices, default=Term.MONTH)
    custom_days = models.PositiveIntegerField(default=0)  # dùng khi term=CUSTOM
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordering", "id"]
        indexes = [models.Index(fields=["product", "ordering"]) ]
        verbose_name = "Gói dịch vụ"
        verbose_name_plural = "Gói dịch vụ"

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    def duration_days(self) -> int:
        if self.term == self.Term.MONTH:
            return 30
        if self.term == self.Term.QUARTER:
            return 90
        if self.term == self.Term.YEAR:
            return 365
        return max(0, int(self.custom_days or 0))


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Đang hiệu lực"
        CANCELLED = "cancelled", "Đã hủy"
        EXPIRED = "expired", "Hết hạn"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    product = models.ForeignKey("Product", on_delete=models.PROTECT, related_name="subscriptions")
    plan = models.ForeignKey("ServicePlan", on_delete=models.PROTECT, related_name="subscriptions")
    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["status", "-started_at"]) ]
        verbose_name = "Đăng ký dịch vụ"
        verbose_name_plural = "Đăng ký dịch vụ"

    def __str__(self):
        return f"{self.user} — {self.product.name} — {self.plan.name}"

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.ends_at and self.plan_id:
            days = self.plan.duration_days()
            if days > 0:
                base = self.started_at or timezone.now()
                self.ends_at = base + timezone.timedelta(days=days)
        return super().save(*args, **kwargs)

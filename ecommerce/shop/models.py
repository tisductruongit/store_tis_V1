# shop/models.py
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator
import re, unicodedata

# --- helpers slug ---
def _slugify_vn(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    return text.strip("-").lower() or "item"

def _unique_slug(model, base_slug: str, instance=None) -> str:
    qs = model.objects.all()
    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)
    candidate = base_slug
    i = 1
    while qs.filter(slug=candidate).exists():
        candidate = f"{base_slug}-{i}"
        i += 1
    return candidate

# --- upload_to ---
def product_main_image_path(instance, filename):
    # ảnh đại diện: products/<product-slug>/<filename>
    return f"products/{instance.slug}/{filename}"

def product_extra_image_path(instance, filename):
    # ảnh bổ sung: products/<product-slug>/<filename>
    return f"products/{instance.product.slug}/{filename}"

class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self): return self.name

    def save(self, *args, **kwargs):
        base = _slugify_vn(self.slug or self.name)
        self.slug = _unique_slug(Category, base, self)
        super().save(*args, **kwargs)

# shop/models.py (trích phần Product)
class Product(models.Model):
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    name = models.CharField(max_length=200, unique=True)  # ⬅️ KHÔNG cho trùng tên
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to=product_main_image_path, blank=True, null=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    ...


    class Meta:
        ordering = ["-created_at"]

    def __str__(self): return self.name
    def get_absolute_url(self): return reverse("shop:product_detail", args=[self.slug])

    def save(self, *args, **kwargs):
        # Đặt slug (auto +1 nếu trùng) TRƯỚC khi gọi super().save()
        base = _slugify_vn(self.slug or self.name)
        self.slug = _unique_slug(Product, base, self)
        super().save(*args, **kwargs)

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to=product_extra_image_path)  # <-- vào products/<slug>/
    alt = models.CharField(max_length=200, blank=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordering", "id"]

    def __str__(self): return f"{self.product.name} - #{self.pk}"

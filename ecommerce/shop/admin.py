from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "category", "price", "stock", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_editable = ("price", "stock")
    readonly_fields = ("created_at",)
    inlines = [ProductImageInline]  # ⬅️ cho phép thêm nhiều ảnh

    fieldsets = (
        ("Thông tin", {"fields": ("category", "name", "slug", "description")}),
        ("Ảnh đại diện (tuỳ chọn)", {"fields": ("image",)}),
        ("Bán hàng", {"fields": ("price", "stock")}),
        ("Khác", {"fields": ("created_at",)}),
    )

    def thumb(self, obj):
        src = obj.image.url if obj.image else (obj.images.first().image.url if obj.images.first() else "")
        if src:
            return format_html('<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />', src)
        return "—"
    thumb.short_description = "Ảnh"

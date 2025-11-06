from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage

# shop/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # ➕ Hiển thị supplier trên danh sách
    list_display = ("thumb", "name", "category", "supplier", "price", "stock", "created_at")
    list_filter = ("category", "created_at")  # có thể thêm "supplier" nếu danh sách nhà cung cấp ổn định
    search_fields = ("name", "description", "supplier")
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_editable = ("price", "stock")
    readonly_fields = ("created_at",)
    inlines = [ProductImageInline]

    # ➕ Đưa supplier vào nhóm “Thông tin” để sửa được trong form admin
    fieldsets = (
        ("Thông tin", {"fields": ("category", "name", "slug", "supplier", "description")}),
        ("Ảnh đại diện (tuỳ chọn)", {"fields": ("image",)}),
        ("Bán hàng", {"fields": ("price", "stock")}),
        ("Khác", {"fields": ("created_at",)}),
    )

    def thumb(self, obj):
        src = obj.image.url if obj.image else (obj.images.first().image.url if obj.images.first() else "")
        if src:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />', src
            )
        return "—"
    thumb.short_description = "Ảnh"




# shop/admin.py
# shop/admin.py
from django.contrib import admin
from .models import ConsultationRequest

@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'customer_phone', 'product', 'status', 'handled_by', 'created_at', 'handled_at')
    list_filter = ('status', 'created_at', 'handled_by')
    search_fields = ('user__username', 'customer_phone', 'product__name')
    autocomplete_fields = ('user', 'product', 'handled_by')
    readonly_fields = ('created_at', 'handled_at')
    actions = ['mark_done']

    @admin.action(description='Đánh dấu ĐÃ tư vấn')
    def mark_done(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='done', handled_by=request.user, handled_at=timezone.now())
        self.message_user(request, f'Đã cập nhật {updated} yêu cầu.')




# shop/admin.py (thêm vào cuối file)
from django.contrib import admin
from .models import Category, Product, ProductImage, ConsultationRequest, Order, OrderItem, PageView, ServicePlan, Subscription

@admin.register(ServicePlan)
class ServicePlanAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "term", "custom_days", "price", "is_active", "ordering")
    list_filter = ("term", "is_active", "product")
    search_fields = ("name", "product__name")
    list_editable = ("price", "is_active", "ordering")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "plan", "started_at", "ends_at", "status")
    list_filter = ("status", "plan__term", "product")
    search_fields = ("user__username", "product__name")

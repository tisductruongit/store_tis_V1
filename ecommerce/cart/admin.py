from django.contrib import admin
from .models import Order, OrderItem

# cart/admin.py
from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id","user","status","total_price","created_at","confirmed_by","confirmed_at","cancelled_by","cancelled_at")
    list_filter  = ("status","created_at","confirmed_at","cancelled_at")
    search_fields = ("id","user__username")

    @admin.action(description="Hủy các đơn đã chọn (nếu đang chờ)")
    def cancel_orders(self, request, queryset):
        for o in queryset.filter(status=Order.Status.PENDING_ADMIN):
            o.cancel(request.user, reason="Hủy từ Django Admin")
        self.message_user(request, "Đã hủy các đơn được chọn.")
    actions = ["cancel_orders"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

# Nếu muốn xem item ngay trong Order (bật inline):
OrderAdmin.inlines = [OrderItemInline]

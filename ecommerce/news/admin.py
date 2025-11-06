# news/admin.py
from django.contrib import admin
from .models import News

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at', 'is_published')
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'body', 'slug')
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ('is_published',)  # cho phép bật/tắt ngay trên list

    actions = ['publish_selected', 'unpublish_selected']

    @admin.action(description="Hiển thị (Publish) các bài đã chọn")
    def publish_selected(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"Đã hiển thị {updated} bài.")

    @admin.action(description="Ẩn (Unpublish) các bài đã chọn")
    def unpublish_selected(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"Đã ẩn {updated} bài.")

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse

from .models import Profile, ProfileImage


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = "user"
    fields = ("phone", "avatar", "avatar_preview", "created_at", "updated_at")
    readonly_fields = ("avatar_preview", "created_at", "updated_at")
    extra = 0

    @admin.display(description="Avatar")
    def avatar_preview(self, obj):
        if obj and obj.avatar:
            return format_html('<img src="{}" style="height:60px;border-radius:8px" />', obj.avatar.url)
        return "-"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "avatar_preview", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "phone")
    readonly_fields = ("avatar_preview", "created_at", "updated_at")

    @admin.display(description="Avatar")
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" style="height:60px;border-radius:8px" />', obj.avatar.url)
        return "-"


@admin.register(ProfileImage)
class ProfileImageAdmin(admin.ModelAdmin):
    list_display = ("profile", "preview", "uploaded_at")
    list_select_related = ("profile", "profile__user")
    search_fields = ("profile__user__username",)
    list_filter = ("uploaded_at",)
    readonly_fields = ("preview",)

    @admin.display(description="Ảnh")
    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:8px" />', obj.image.url)
        return "-"


class UserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]
    list_display = (
        "username", "email", "first_name", "last_name",
        "phone", "is_staff", "is_active", "date_joined", "last_login",
        "avatar_thumb", "profile_link", "photos_count",
    )
    list_select_related = ("profile",)
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name", "profile__phone")
    ordering = ("-date_joined",)
    actions = ["activate_users", "deactivate_users", "export_emails_csv"]

    @admin.display(ordering="profile__phone", description="Phone")
    def phone(self, user):
        return getattr(user.profile, "phone", "")

    @admin.display(description="Avatar")
    def avatar_thumb(self, user):
        a = getattr(user.profile, "avatar", None)
        if a:
            try:
                return format_html('<img src="{}" style="height:40px;border-radius:50%" />', a.url)
            except Exception:
                pass
        return ""

    @admin.display(description="Profile")
    def profile_link(self, user):
        try:
            pk = user.profile.pk
            url = reverse("admin:accounts_profile_change", args=[pk])
            return format_html('<a href="{}">Mở profile</a>', url)
        except Profile.DoesNotExist:
            return "-"

    @admin.display(description="Ảnh")
    def photos_count(self, user):
        try:
            cnt = user.profile.photos.count()
            if cnt:
                url = reverse("admin:accounts_profileimage_changelist") + f"?profile__id__exact={user.profile.id}"
                return format_html('<a href="{}">{} ảnh</a>', url, cnt)
            return "0"
        except Exception:
            return "0"

    @admin.action(description="Kích hoạt tài khoản đã chọn")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Đã bật hoạt động cho {updated} người dùng.")

    @admin.action(description="Vô hiệu hoá tài khoản đã chọn")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Đã vô hiệu hoá {updated} người dùng.")

    @admin.action(description="Xuất CSV (username,email,phone,...)")
    def export_emails_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = "attachment; filename=users.csv"
        w = csv.writer(resp)
        w.writerow(["username","email","first_name","last_name","phone","is_active","is_staff","date_joined"])
        for u in queryset:
            phone = getattr(getattr(u, "profile", None), "phone", "")
            w.writerow([u.username, u.email, u.first_name, u.last_name, phone, u.is_active, u.is_staff, u.date_joined])
        return resp


# Thay UserAdmin mặc định bằng bản tuỳ biến
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

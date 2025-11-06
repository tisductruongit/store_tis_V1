from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/photo/<int:pk>/delete/", views.delete_profile_photo, name="photo_delete"),


    path("manage/users/", views.admin_user_list, name="admin_user_list"),
    path("manage/users/<int:pk>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("manage/users/<int:pk>/toggle-active/", views.admin_user_toggle_active, name="admin_user_toggle_active"),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
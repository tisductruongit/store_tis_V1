# news/urls.py
from django.urls import path
from . import views

app_name = "news"
urlpatterns = [
    path("", views.news_list, name="list"),
    path("<slug:slug>/", views.news_detail, name="detail"),
    path("admin/create/", views.admin_news_create, name="admin_create"),
    path("admin/<int:pk>/edit/", views.admin_news_edit, name="admin_edit"),
    path("admin/<int:pk>/delete/", views.admin_news_delete, name="admin_delete"),
]

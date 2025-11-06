from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('category/<slug:slug>/', views.product_by_category, name='product_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    path('manage/product/create/', views.admin_product_create, name='admin_product_create'),
    path('manage/category/create/', views.admin_category_create, name='admin_category_create'),
    path('manage/category/<slug:slug>/edit/', views.admin_category_update, name='admin_category_update'),
    path('manage/category/<slug:slug>/delete/', views.admin_category_delete, name='admin_category_delete'),

    # đổi sang ID:
    path('manage/product/<int:pk>/edit/', views.admin_product_update, name='admin_product_update'),
    path('manage/product/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path("manage/api/check-product-name/", views.check_product_name, name="check_product_name"),

]

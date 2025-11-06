from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path("", views.home, name="home"),
    path('list/', views.product_list, name='product_list'),
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
    
    
    path('consult/request/<int:product_id>/', views.consult_request, name='consult_request'),
    path('manage/consults/', views.consult_list, name='consult_list'),
    path('manage/consults/<int:pk>/done/', views.consult_mark_done, name='consult_mark_done'),
    
    
    # Tạo đơn từ yêu cầu tư vấn
    path('manage/consults/<int:pk>/create-order/', views.consult_create_order, name='consult_create_order'),
    # Xem đơn
    path('manage/orders/<int:order_id>/', views.order_detail, name='order_detail'),




    path('manage/reports/', views.admin_reports, name='admin_reports'),
    path('manage/reports/data/', views.admin_reports_data, name='admin_reports_data'),
    path('manage/reports/export/', views.admin_reports_export, name='admin_reports_export'),
    
    # Quản lý gói dịch vụ
    path('manage/product/<int:product_id>/plans/create/', views.admin_serviceplan_create, name='admin_serviceplan_create'),
    path('manage/plans/<int:pk>/edit/', views.admin_serviceplan_update, name='admin_serviceplan_update'),
    path('manage/plans/<int:pk>/delete/', views.admin_serviceplan_delete, name='admin_serviceplan_delete'),
    
    # API cho gói dịch vụ
    path('api/plans/<int:product_id>/', views.api_product_plans, name='api_product_plans'),
]

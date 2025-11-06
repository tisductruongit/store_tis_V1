# cart/urls.py
from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    # ====== CART UI ======
    path("", views.cart_detail, name="cart_detail"),
    path("add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("update/<int:product_id>/", views.cart_update, name="cart_update"),

    # ====== TƯ VẤN SẢN PHẨM ======
    path("consult-request/", views.consult_request, name="consult_request"),

    # ====== CHECKOUT / TẠO ĐƠN (USER) ======
    path("checkout/", views.checkout_create_order, name="checkout"),
    path("checkout/success/<int:order_id>/", views.checkout_success, name="checkout_success"),

    # ====== LỊCH SỬ & CHI TIẾT ĐƠN (USER) ======
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:order_id>/", views.order_detail_user, name="order_detail"),

    # ====== ADMIN DUYỆT ĐƠN ======
    path("admin/orders/pending/", views.admin_pending_orders, name="admin_pending_orders"),
    path("admin/orders/<int:order_id>/confirm/", views.admin_confirm_order, name="admin_confirm_order"),
    path("admin/orders/<int:order_id>/cancel/", views.admin_cancel_order, name="admin_cancel_order"),
    path("admin/orders/confirmed/", views.admin_confirmed_orders, name="admin_confirmed_orders"),
]

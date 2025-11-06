# cart/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.urls import reverse

from shop.models import Product
from .cart import Cart

@require_POST
def cart_add(request, product_id):
    # Chưa đăng nhập -> đẩy qua trang login và hiện thông báo
    if not request.user.is_authenticated:
        messages.info(request, "Vui lòng đăng nhập để thêm đơn hàng.")
        # Quay về trang hiện tại sau khi login xong
        referer = request.META.get("HTTP_REFERER") or reverse("shop:product_list")
        login_url = reverse("accounts:login") + f"?next={referer}"
        return JsonResponse({"ok": False, "require_login": True, "redirect": login_url})

    # Đã đăng nhập -> thêm vào giỏ như bình thường
    cart = Cart(request)  # dùng Cart session hiện có:contentReference[oaicite:1]{index=1}
    product = get_object_or_404(Product, pk=product_id)
    cart.add(product_id, quantity=1)

    return JsonResponse({
        "ok": True,
        "message": f"Đã thêm “{product.name}” vào giỏ hàng.",
        "total_items": len(cart),
        "product_id": product_id,
    })


def cart_remove(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return JsonResponse({"ok": True, "total_items": len(cart)})

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart_obj': cart})

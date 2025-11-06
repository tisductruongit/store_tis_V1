# cart/cart.py
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Iterator, List

from django.conf import settings
from django.utils.functional import cached_property

# Đổi tên key nếu bạn muốn; đảm bảo thống nhất trong context processor & views
CART_SESSION_ID = getattr(settings, "CART_SESSION_ID", "cart")


class Cart:
    """
    Lưu giỏ hàng vào session theo cấu trúc:
    session[CART_SESSION_ID] = {
        "<product_id>": {
            "quantity": int,
            "price": "decimal-as-string"
        },
        ...
    }

    LƯU Ý:
    - KHÔNG lưu object Product vào session (tránh lỗi JSON serializable).
    - Chỉ xóa các item đã thanh toán ở bước checkout; KHÔNG gọi clear().
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if cart is None:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart: Dict[str, Dict] = cart

    # -------------------- Core helpers --------------------
    def save(self) -> None:
        """Đánh dấu session đã thay đổi."""
        self.session[CART_SESSION_ID] = self.cart
        self.session.modified = True

    def _norm_id(self, product_id) -> str:
        """Ép id về chuỗi để làm key nhất quán."""
        return str(product_id)

    # -------------------- Public API ----------------------
    def add(self, product, quantity: int = 1, override_quantity: bool = False, price: Decimal | None = None) -> None:
        """
        Thêm/ cập nhật một sản phẩm vào giỏ.
        - product: model Product
        - quantity: số lượng cộng thêm (hoặc set mới nếu override_quantity=True)
        - price: đơn giá (nếu None sẽ lấy product.price)
        """
        pid = self._norm_id(product.id)
        if price is None:
            price = getattr(product, "price", Decimal("0")) or Decimal("0")

        if pid not in self.cart:
            self.cart[pid] = {"quantity": 0, "price": str(price)}
        if override_quantity:
            self.cart[pid]["quantity"] = max(int(quantity or 0), 0)
        else:
            self.cart[pid]["quantity"] = int(self.cart[pid]["quantity"]) + int(quantity or 0)

        if self.cart[pid]["quantity"] <= 0:
            # tự động loại bỏ nếu số lượng <= 0
            del self.cart[pid]

        self.save()

    def update(self, product_id, quantity: int) -> None:
        """Set số lượng tuyệt đối cho một item; nếu <=0 thì xóa."""
        pid = self._norm_id(product_id)
        if pid not in self.cart:
            return
        qty = int(quantity or 0)
        if qty <= 0:
            del self.cart[pid]
        else:
            self.cart[pid]["quantity"] = qty
        self.save()

    def remove(self, product_id) -> None:
        """Xóa một sản phẩm khỏi giỏ."""
        pid = self._norm_id(product_id)
        if pid in self.cart:
            del self.cart[pid]
            self.save()

    def remove_many(self, product_ids: Iterable) -> None:
        """Xóa nhiều sản phẩm (dùng sau khi checkout các mục đã chọn)."""
        for pid in product_ids:
            self.cart.pop(self._norm_id(pid), None)
        self.save()

    def clear(self) -> None:
        """
        XÓA TOÀN BỘ giỏ hàng.
        ⚠️ Không dùng khi checkout mục đã chọn – chỉ phục vụ các trường hợp như user bấm 'Xóa tất cả'.
        """
        if CART_SESSION_ID in self.session:
            del self.session[CART_SESSION_ID]
            self.session.modified = True
        self.cart = {}

    # -------------------- Read-only helpers ----------------
    def __iter__(self) -> Iterator[dict]:
        """
        Lặp qua các item, kèm product thực tế & tổng dòng.
        Truy vấn product 1 lần cho toàn giỏ để tránh N+1.
        """
        from shop.models import Product  # import chậm để tránh vòng lặp import

        product_ids: List[str] = list(self.cart.keys())
        products = Product.objects.filter(id__in=product_ids)
        product_map = {str(p.id): p for p in products}

        for pid, data in self.cart.items():
            product = product_map.get(pid)
            # nếu product đã bị xóa khỏi DB, bỏ qua item rác
            if not product:
                continue
            price = Decimal(str(data.get("price", "0")))
            qty = int(data.get("quantity", 0))
            yield {
                "product": product,
                "price": price,
                "quantity": qty,
                "total_price": price * qty,
                "product_id": int(pid),
            }

    def __len__(self) -> int:
        """Tổng số lượng sản phẩm (sum quantity)."""
        return sum(int(item["quantity"]) for item in self.cart.values())

    @property
    def total_quantity(self) -> int:
        """Alias cho tổng số lượng."""
        return len(self)

    @property
    def subtotal(self) -> Decimal:
        """Tổng tiền của giỏ (không phí/thuế)."""
        total = Decimal("0")
        for item in self:
            total += item["total_price"]
        return total

    @property
    def total_price(self) -> Decimal:
        """Alias cho subtotal (giữ tương thích cũ)."""
        return self.subtotal

    @cached_property
    def is_empty(self) -> bool:
        return not bool(self.cart)




# cart/views.py
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .cart import Cart
from .models import Order, OrderItem
from shop.models import Product


@login_required
@require_POST
def checkout_create_order(request):
    """Nhận JSON: {"items":[{"product_id":13,"quantity":2}, ...]} từ modal xác nhận."""
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    items = []
    if request.content_type.startswith("application/json"):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
            items = payload.get("items") or []
        except Exception:
            items = []

    # Fallback nếu sau này bạn cũng submit form (không dùng modal)
    if not items:
        ids = request.POST.getlist("selected_item_ids")
        items = [{"product_id": int(x), "quantity": 0} for x in ids]  # qty sẽ lấy trong cart

    cart = Cart(request)
    # chỉ giữ những item thật sự đang có trong giỏ
    selected = []
    for obj in items:
        pid = str(obj.get("product_id"))
        if pid in cart.cart:
            qty = int(obj.get("quantity") or cart.cart[pid]["quantity"] or 1)
            selected.append((pid, qty))

    if not selected:
        if is_ajax:
            return JsonResponse({"ok": False, "message": "Bạn chưa chọn sản phẩm nào."}, status=400)
        return redirect("cart:cart_detail")

    with transaction.atomic():
        order = Order.objects.create(user=request.user, status=Order.Status.PENDING_ADMIN)

        pids = [int(pid) for pid, _ in selected]
        product_map = {str(p.id): p for p in Product.objects.filter(id__in=pids)}

        bulk = []
        for pid, qty in selected:
            prod = product_map.get(pid)
            if not prod:
                continue
            unit_price = Decimal(str(cart.cart[pid]["price"]))  # giá đã lưu trong session
            bulk.append(OrderItem(order=order, product=prod, quantity=qty, price=unit_price))
        OrderItem.objects.bulk_create(bulk)

        # chỉ xóa khỏi giỏ các mục đã đặt
        for pid, _ in selected:
            cart.remove(pid)
        cart.save()

    if is_ajax:
        return JsonResponse({"ok": True, "redirect_url": reverse("cart:checkout_success", args=[order.id])})
    return redirect("cart:checkout_success", order_id=order.id)

# cart/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from django.urls import reverse
from shop.models import Product, ConsultationRequest


from shop.models import Product
from .cart import Cart

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from .cart import Cart
from shop.models import Product

# cart/views.py
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from .cart import Cart
from shop.models import Product

def _resolve_product_price(product) -> Decimal:
    # thứ tự ưu tiên – sửa theo model của bạn nếu cần
    candidates = ["price", "unit_price", "sale_price", "final_price", "premium", "retail_price", "amount"]
    for name in candidates:
        if hasattr(product, name):
            val = getattr(product, name)
            if val not in (None, "", 0):
                try:
                    return Decimal(str(val))
                except Exception:
                    pass
    return Decimal("0")

from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from shop.models import Product, ServicePlan
from .cart import Cart


def cart_add(request, product_id: int):
    # Bắt buộc đăng nhập
    if not request.user.is_authenticated:
        referer = request.META.get("HTTP_REFERER") or reverse("shop:product_list")
        return JsonResponse({
            "ok": False,
            "require_login": True,
            "redirect": f"{reverse('accounts:login')}?next={referer}"
        })

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id, is_active=True)

    # Lấy đơn giá linh hoạt
    for f in ("price", "unit_price", "sale_price", "final_price", "premium"):
        if hasattr(product, f) and getattr(product, f) not in (None, "", 0):
            unit_price = Decimal(str(getattr(product, f)))
            break
    else:
        unit_price = Decimal("0")

    # Lấy số lượng
    try:
        qty = int(request.POST.get("quantity", 1) or 1)
    except ValueError:
        qty = 1
    if qty <= 0:
        qty = 1

    # Xử lý ServicePlan (nếu product có kế hoạch thì bắt buộc chọn)
    plan = None
    available_plans = ServicePlan.objects.filter(product=product, is_active=True).order_by("ordering", "id")
    if available_plans.exists():
        plan_id = request.POST.get("plan_id")
        if not plan_id:
            return JsonResponse({"ok": False, "error": "Vui lòng chọn thời hạn dịch vụ."}, status=400)
        try:
            plan = available_plans.get(pk=int(plan_id))
        except (ValueError, ServicePlan.DoesNotExist):
            return JsonResponse({"ok": False, "error": "Gói dịch vụ không hợp lệ."}, status=400)

        # Nếu muốn tính giá theo gói:
        if getattr(plan, "price", None) not in (None, "", 0):
            unit_price = Decimal(str(plan.price))

    # => Gọi cart.add KHÔNG dùng kwargs lạ
    cart.add(product, quantity=qty, price=unit_price)

    # Lưu mapping plan vào session để dùng ở bước checkout
    if plan:
        plans = request.session.get("cart_plans", {})
        plans[str(product.id)] = {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "plan_term": plan.term,
            "plan_days": plan.duration_days(),
            "plan_price": str(plan.price) if getattr(plan, "price", None) not in (None, "", 0) else None,
        }
        request.session["cart_plans"] = plans
        request.session.modified = True

    return JsonResponse({
        "ok": True,
        "product_id": product.id,
        "qty": qty,
        "total_items": len(cart),
        "plan": ({
            "id": plan.id,
            "name": plan.name,
            "term": plan.term,
            "days": plan.duration_days(),
        } if plan else None)
    })


# --- API cập nhật số lượng ---
# imports thêm/đủ
# cart/views.py
# cart/views.py (tiếp)
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

@require_POST
def cart_update(request, product_id: int):
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:login')}?next={reverse('cart:cart_detail')}"
        return JsonResponse({"ok": False, "require_login": True, "redirect": login_url})

    cart = Cart(request)
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    cart.update(product_id, qty)

    pid = str(product_id)
    if pid in cart.cart:
        price = Decimal(str(cart.cart[pid]["price"]))
        line_total = float(price * Decimal(cart.cart[pid]["quantity"]))
        quantity = int(cart.cart[pid]["quantity"])
    else:
        line_total = 0.0
        quantity = 0

    return JsonResponse({"ok": True, "quantity": quantity, "line_total": line_total, "total_items": len(cart)})


@require_POST
def cart_remove(request, product_id: int):
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:login')}?next={reverse('cart:cart_detail')}"
        return JsonResponse({"ok": False, "require_login": True, "redirect": login_url})
    cart = Cart(request)
    cart.remove(product_id)
    return JsonResponse({"ok": True, "total_items": len(cart)})



def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart/cart.html', {'cart_obj': cart})


from django.views.decorators.http import require_POST
from django.http import JsonResponse

# --- CẬP NHẬT HÀNH VI consult_request: lưu về admin ---
@require_POST
def consult_request(request):
    """
    Nhận: name, phone, note, product_id, product_name
    Lưu thành ConsultationRequest (app shop) để admin xử lý.
    """
    name = (request.POST.get("name") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    note = (request.POST.get("note") or "").strip()
    pid = request.POST.get("product_id")

    if not (name and phone and pid):
        return JsonResponse({"ok": False, "message": "Thiếu thông tin bắt buộc."}, status=400)

    product = get_object_or_404(Product, pk=pid)

    # Tạo ticket tư vấn cho admin (status mặc định pending)
    ConsultationRequest.objects.create(
        user=request.user if request.user.is_authenticated else None,
        product=product,
        note=f"[{name}] {note}".strip(),
        customer_phone=phone,
    )
    return JsonResponse({"ok": True, "message": "Đã ghi nhận yêu cầu. Bộ phận tư vấn sẽ liên hệ sớm!"})


# cart/views.py
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from decimal import Decimal
import json

from .cart import Cart
from .models import Order, OrderItem
from shop.models import Product
# cart/views.py
# cart/views.py
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from decimal import Decimal
import json

from .cart import Cart
from .models import Order, OrderItem
from shop.models import Product


@login_required
@require_POST
def checkout_create_order(request):
    """Xử lý đặt hàng từ form hoặc từ AJAX."""
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    cart = Cart(request)

    items = []
    if request.content_type.startswith("application/json"):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
            items = payload.get("items") or []
        except Exception:
            items = []

    if not items:
        # fallback: lấy từ form
        ids = request.POST.getlist("selected_item_ids")
        items = [{"product_id": int(x), "quantity": 0} for x in ids]

    # lọc item còn trong giỏ
    selected = []
    for obj in items:
        pid = str(obj.get("product_id"))
        if pid in cart.cart:
            qty = int(obj.get("quantity") or cart.cart[pid]["quantity"] or 1)
            selected.append((pid, qty))

    if not selected:
        if is_ajax:
            return JsonResponse({"ok": False, "message": "Bạn chưa chọn sản phẩm nào."}, status=400)
        messages.error(request, "Bạn chưa chọn sản phẩm nào để thanh toán.")
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
            unit_price = Decimal(str(cart.cart[pid]["price"]))
            bulk.append(OrderItem(order=order, product=prod, quantity=qty, price=unit_price))
        OrderItem.objects.bulk_create(bulk)

        # xóa item đã đặt khỏi giỏ
        for pid, _ in selected:
            cart.remove(pid)
        cart.save()

    # trả về cho AJAX hoặc redirect thường
    if is_ajax:
        return JsonResponse({"ok": True, "redirect_url": reverse("cart:checkout_success", args=[order.id])})
    return redirect("cart:checkout_success", order_id=order.id)


@login_required
def checkout_success(request, order_id: int):
    """Trang hiển thị sau khi tạo đơn thành công."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, "cart/checkout_success.html", {"order": order})




# cart/views.py (thêm import)
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from .models import Order

@login_required
def order_history(request):
    """
    Danh sách đơn hàng của chính user (mới nhất trước).
    Hỗ trợ lọc theo ?status=...
    """
    qs = (Order.objects
          .filter(user=request.user)
          .prefetch_related("items__product")
          .order_by("-created_at"))

    # Lọc trạng thái nếu truyền lên
    status = (request.GET.get("status") or "").upper().strip()
    valid_statuses = {s for s, _ in Order.Status.choices}
    if status in valid_statuses:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 10)  # 10 đơn / trang
    page = request.GET.get("page") or 1
    orders = paginator.get_page(page)

    # Map trạng thái -> màu badge (không phụ thuộc CSS riêng)
    badge_map = {
        Order.Status.PENDING_ADMIN: {"bg": "#FEF3C7", "fg": "#92400E"},  # vàng nhạt
        Order.Status.CONFIRMED:     {"bg": "#DCFCE7", "fg": "#065F46"},  # xanh
        Order.Status.CANCELLED:     {"bg": "#FEE2E2", "fg": "#991B1B"},  # đỏ
        Order.Status.DRAFT:         {"bg": "#E5E7EB", "fg": "#111827"},  # xám
    }

    return render(request, "cart/order_history.html", {
        "orders": orders,
        "current_status": status,
        "badge_map": badge_map,
        "all_statuses": Order.Status.choices,  # để build bộ lọc
    })


# cart/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

@login_required
def order_detail_user(request, order_id: int):
    """
    Chi tiết 1 đơn của user (chỉ cho xem đơn của chính mình).
    """
    order = get_object_or_404(
        Order.objects.select_related("user").prefetch_related("items__product"),
        pk=order_id, user=request.user
    )

    badge_map = {
        Order.Status.PENDING_ADMIN: {"bg": "#FEF3C7", "fg": "#92400E"},  # vàng nhạt
        Order.Status.CONFIRMED:     {"bg": "#DCFCE7", "fg": "#065F46"},  # xanh
        Order.Status.CANCELLED:     {"bg": "#FEE2E2", "fg": "#991B1B"},  # đỏ
        Order.Status.DRAFT:         {"bg": "#E5E7EB", "fg": "#111827"},  # xám
    }
    bm = badge_map.get(order.status, {"bg": "#E5E7EB", "fg": "#111827"})

    return render(request, "cart/order_cart.html", {
        "order": order,
        "bm": bm,                     # << dùng trực tiếp trong template
    })



# cart/views.py
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Order

@staff_member_required
def admin_pending_orders(request):
    """Trang liệt kê các đơn CHỜ xác nhận + hiển thị chi tiết từng item."""
    qs = (Order.objects
          .filter(status=Order.Status.PENDING_ADMIN)
          .select_related("user")
          .prefetch_related("items__product")
          .order_by("created_at"))  # cũ trước

    paginator = Paginator(qs, 10)
    orders = paginator.get_page(request.GET.get("page") or 1)

    # thêm danh sách đã xác nhận gần đây (hiển thị dưới cùng – tùy chọn)
    recent_confirmed = (Order.objects
                        .filter(status=Order.Status.CONFIRMED)
                        .select_related("confirmed_by", "user")
                        .prefetch_related("items__product")
                        .order_by("-confirmed_at")[:10])

    return render(request, "cart/admin_pending_orders.html", {
        "orders": orders,
        "recent_confirmed": recent_confirmed,
    })

@staff_member_required
@require_POST
def admin_confirm_order(request, order_id: int):
    """Xác nhận đơn đang PENDING_ADMIN."""
    order = get_object_or_404(Order, pk=order_id, status=Order.Status.PENDING_ADMIN)
    order.confirm(request.user)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "order_id": order.id,
            "confirmed_by": request.user.username,
            "confirmed_at": order.confirmed_at.isoformat(),
        })
    messages.success(request, f"Đã xác nhận đơn #{order.id}.")
    return redirect("cart:admin_pending_orders")

@staff_member_required
@require_POST
def admin_cancel_order(request, order_id: int):
    """Hủy đơn đang PENDING_ADMIN (có lý do hủy tùy chọn)."""
    order = get_object_or_404(Order, pk=order_id, status=Order.Status.PENDING_ADMIN)
    reason = (request.POST.get("reason") or "").strip()
    order.cancel(request.user, reason=reason)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "order_id": order.id,
            "cancelled_by": request.user.username,
            "cancelled_at": order.cancelled_at.isoformat(),
            "reason": order.cancel_reason,
        })
    messages.success(request, f"Đã hủy đơn #{order.id}.")
    return redirect("cart:admin_pending_orders")


# cart/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from .models import Order

@staff_member_required
def admin_confirmed_orders(request):
    """
    Trang liệt kê tất cả đơn đã xác nhận.
    - Lọc q: theo mã đơn (id) hoặc username người mua
    - Lọc theo khoảng ngày xác nhận: date_from, date_to (YYYY-MM-DD)
    - Phân trang
    """
    qs = (Order.objects
          .filter(status=Order.Status.CONFIRMED)
          .select_related("user", "confirmed_by")
          .prefetch_related("items__product")
          .order_by("-confirmed_at", "-created_at"))

    q = (request.GET.get("q") or "").strip()
    if q:
        if q.isdigit():
            qs = qs.filter(Q(id=int(q)) | Q(user__username__icontains=q))
        else:
            qs = qs.filter(user__username__icontains=q)

    date_from = (request.GET.get("date_from") or "").strip()
    date_to   = (request.GET.get("date_to") or "").strip()
    # lọc theo ngày xác nhận (nếu có)
    if date_from:
        qs = qs.filter(confirmed_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(confirmed_at__date__lte=date_to)

    paginator = Paginator(qs, 15)  # 15 đơn/trang (điều chỉnh tùy ý)
    page = request.GET.get("page") or 1
    orders = paginator.get_page(page)

    return render(request, "cart/admin_confirmed_orders.html", {
        "orders": orders,
        "q": q,
        "date_from": date_from,
        "date_to": date_to,
    })

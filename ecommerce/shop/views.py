# shop/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, HttpRequest  

from .forms import CategoryForm, ProductForm, ProductImagesForm, ServicePlanForm
from .models import Category, Product, ProductImage, ConsultationRequest

# (tuỳ dự án) nếu có app news
try:
    from news.models import News  # type: ignore
except Exception:
    News = None

# ---------- Helpers ----------

def _is_ajax(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

def _get_user_phone(user) -> str:
    """Lấy SĐT từ các profile phổ biến, nếu có."""
    phone = ""
    # profile mặc định
    prof = getattr(user, "profile", None)
    if prof and getattr(prof, "phone", None):
        phone = prof.phone
    # thử các tên khác
    if not phone:
        for attr in ("userprofile", "customer", "info"):
            obj = getattr(user, attr, None)
            if obj and getattr(obj, "phone", None):
                phone = obj.phone
                break
    return str(phone or "")

# Prefetch ảnh phụ hợp lệ
VALID_IMAGES_PREFETCH = Prefetch(
    "images",
    queryset=ProductImage.objects.filter(image__isnull=False).exclude(image="").order_by("ordering", "id"),
)



from django.db.models import Prefetch
from django.shortcuts import render
from .models import Category, Product, ProductImage

# import model News đúng app của bạn
from news.models import News   # đổi path nếu khác

# shop/views.py (home)
from django.db.models import Prefetch
from django.shortcuts import render
from shop.models import Category, Product, ProductImage, ServicePlan
from news.models import News

def home(request):
    categories = Category.objects.all().order_by("name")

    img_qs   = ProductImage.objects.all()
    plan_qs  = ServicePlan.objects.filter(is_active=True).order_by("ordering", "id")

    sections = []
    for c in categories:
        products = (
            Product.objects.filter(category=c, is_active=True)
            .select_related("category")
            .prefetch_related(
                Prefetch("images", queryset=img_qs),
                Prefetch("plans",  queryset=plan_qs),
            )
            .order_by("-created_at")[:8]
        )
        if products:
            sections.append({"category": c, "products": products})

    latest_news = News.objects.filter(is_published=True).order_by("-published_at", "-id")[:6]

    return render(request, "shop/home.html", {
        "sections": sections,
        "latest_news": latest_news,
    })








# ---------- Public pages ----------
from news.models import News  # <— thêm dòng này

def product_list(request):
    q = (request.GET.get("q") or "").strip()
    categories = Category.objects.all().order_by("name")

    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related(VALID_IMAGES_PREFETCH)
        .order_by("-created_at")
    )
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )

    paginator = Paginator(qs, 12)
    try:
        page = paginator.page(int(request.GET.get("page", 1)))
    except (PageNotAnInteger, ValueError):
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    # Lấy 3 tin mới nhất có ảnh để slider chắc chắn có gì đó hiển thị
    # shop/views.py
    latest_news = (
        News.objects.only('slug','title','image','published_at')
        .filter(image__isnull=False)
        .order_by('-published_at')[:5]
    )

    
    ctx = {
        "products": page.object_list,
        "categories": categories,
        "active_category": None,
        "latest_news": latest_news,
        "page_obj": page,
        "paginator": paginator,
        "q": q,
    }
    return render(request, "shop/product_list.html", ctx)



def product_by_category(request, slug):
    """
    Danh sách theo danh mục.
    """
    category = get_object_or_404(Category, slug=slug)
    qs = (
        Product.objects.filter(category=category, is_active=True)
        .select_related("category")
        .prefetch_related(VALID_IMAGES_PREFETCH)
        .order_by("-created_at")
    )

    paginator = Paginator(qs, 12)
    try:
        page = paginator.page(int(request.GET.get("page", 1)))
    except (PageNotAnInteger, ValueError):
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    latest_news = News.objects.order_by("-published_at")[:3] if News else []

    ctx = {
        "products": page.object_list,
        "categories": Category.objects.all().order_by("name"),
        "active_category": category,
        "latest_news": latest_news,
        "page_obj": page,
        "paginator": paginator,
    }
    return render(request, "shop/product_list.html", ctx)


def product_detail(request, slug):
    """
    Chi tiết sản phẩm + gallery ảnh phụ.
    """
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related(VALID_IMAGES_PREFETCH),
        slug=slug,
        is_active=True,
    )
    return render(request, "shop/product_detail.html", {"product": product})

# ---------- Consultation (yêu cầu tư vấn) ----------

@login_required
@require_POST
def consult_request(request, product_id: int):
    """
    Khách xác nhận cần tư vấn 1 sản phẩm:
    - Chống spam: chặn gửi lặp trong 2 phút.
    - Lưu snapshot SĐT tại thời điểm gửi.
    - AJAX: trả JSON {ok, message}; non-AJAX: messages + redirect.
    """
    product = get_object_or_404(Product, pk=product_id, is_active=True)

    # chống spam
    recent = timezone.now() - timezone.timedelta(minutes=2)
    if ConsultationRequest.objects.filter(
        user=request.user, product=product, status="pending", created_at__gte=recent
    ).exists():
        msg = "Bạn đã gửi yêu cầu tư vấn gần đây. Vui lòng đợi nhân viên liên hệ."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "message": msg}, status=200)
        messages.info(request, msg)
        return redirect(request.META.get("HTTP_REFERER") or reverse("shop:product_detail", args=[product.slug]))

    # tạo mới
    phone = _get_user_phone(request.user)
    ConsultationRequest.objects.create(
        user=request.user,
        product=product,
        customer_phone=phone,
    )

    msg = f'Đã ghi nhận yêu cầu tư vấn cho “{product.name}”. Nhân viên sẽ liên hệ sớm.'
    if _is_ajax(request):
        return JsonResponse({"ok": True, "message": msg}, status=200)
    messages.success(request, msg)
    return redirect(request.META.get("HTTP_REFERER") or reverse("shop:product_detail", args=[product.slug]))



@user_passes_test(lambda u: u.is_staff)
def consult_list(request):
    """
    Trang staff xem yêu cầu tư vấn.
    ?status=pending|done (mặc định pending)
    """
    status = request.GET.get("status") or "pending"
    qs = ConsultationRequest.objects.select_related("user", "product", "handled_by")
    if status in ("pending", "done"):
        qs = qs.filter(status=status)

    paginator = Paginator(qs.order_by("-created_at"), 30)
    try:
        page = paginator.page(int(request.GET.get("page", 1)))
    except (PageNotAnInteger, ValueError):
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return render(
        request,
        "shop/consult_list.html",
        {"items": page.object_list, "status": status, "page_obj": page, "paginator": paginator},
    )


# shop/views.py  (chỉ thay trong consult_mark_done)
@user_passes_test(lambda u: u.is_staff)
@require_POST
def consult_mark_done(request, pk: int):
    obj = get_object_or_404(ConsultationRequest, pk=pk)
    obj.status = "done"
    obj.handled_by = request.user
    obj.handled_at = timezone.now()
    note = (request.POST.get("note") or "").strip()
    if note:
        obj.note = note
        obj.save(update_fields=["status", "handled_by", "handled_at", "note"])
    else:
        obj.save(update_fields=["status", "handled_by", "handled_at"])
    if _is_ajax(request):
        return JsonResponse({"ok": True})
    messages.success(request, "Đã đánh dấu ĐÃ tư vấn.")
    return redirect("shop:consult_list")


# ---------- Admin: Product & Category (staff only) ----------

@user_passes_test(lambda u: u.is_staff)
def admin_product_create(request):
    """
    Tạo sản phẩm + upload ảnh phụ (field tên 'images', multiple).
    """
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        images_form = ProductImagesForm()
        if form.is_valid():
            product = form.save()
            # Ảnh phụ (multiple)
            for f in request.FILES.getlist("images"):
                ProductImage.objects.create(product=product, image=f)
            messages.success(request, "Đã tạo sản phẩm thành công.")
            return redirect("shop:product_detail", slug=product.slug)
        messages.error(request, "Dữ liệu chưa hợp lệ, vui lòng kiểm tra.")
    else:
        form = ProductForm()
        images_form = ProductImagesForm()
    return render(request, "shop/admin_product_form.html", {"form": form, "images_form": images_form})


@user_passes_test(lambda u: u.is_staff)
def admin_product_update(request, pk):
    """
    Sửa sản phẩm: có thể xoá ảnh phụ bằng danh sách ID trong 'delete_images'.
    """
    product = get_object_or_404(Product.objects.prefetch_related(VALID_IMAGES_PREFETCH), pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        images_form = ProductImagesForm()
        if form.is_valid():
            form.save()
            # xoá ảnh phụ được chọn
            del_ids = [int(x) for x in request.POST.getlist("delete_images") if str(x).isdigit()]
            if del_ids:
                ProductImage.objects.filter(product=product, id__in=del_ids).delete()
            # thêm ảnh phụ mới
            for f in request.FILES.getlist("images"):
                ProductImage.objects.create(product=product, image=f)
            messages.success(request, "Đã cập nhật sản phẩm.")
            return redirect("shop:product_detail", slug=product.slug)
        messages.error(request, "Dữ liệu chưa hợp lệ, vui lòng kiểm tra.")
    else:
        form = ProductForm(instance=product)
        images_form = ProductImagesForm()
    return render(
        request,
        "shop/admin_product_form.html",
        {"form": form, "images_form": images_form, "product": product, "is_edit": True},
    )


@user_passes_test(lambda u: u.is_staff)
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, f"Đã xoá sản phẩm: {name}")
        return redirect("shop:product_list")
    return render(request, "shop/admin_product_confirm_delete.html", {"product": product})


@user_passes_test(lambda u: u.is_staff)
def admin_category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, "Đã tạo danh mục.")
            return redirect("shop:product_by_category", slug=cat.slug)
        messages.error(request, "Dữ liệu chưa hợp lệ.")
    else:
        form = CategoryForm()
    return render(request, "shop/admin_category_form.html", {"form": form})


@user_passes_test(lambda u: u.is_staff)
def admin_category_update(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật danh mục.")
            return redirect("shop:product_by_category", slug=category.slug)
        messages.error(request, "Dữ liệu chưa hợp lệ.")
    else:
        form = CategoryForm(instance=category)
    return render(request, "shop/admin_category_form.html", {"form": form, "category": category, "is_edit": True})


@user_passes_test(lambda u: u.is_staff)
def admin_category_delete(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == "POST":
        count = category.products.count()
        category.delete()
        messages.success(
            request,
            f"Đã xoá danh mục (và {count} sản phẩm liên quan)." if count else "Đã xoá danh mục.",
        )
        return redirect("shop:product_list")
    return render(
        request,
        "shop/admin_category_confirm_delete.html",
        {"category": category, "product_count": category.products.count()},
    )

# ---------- AJAX utilities (staff) ----------

@require_GET
@user_passes_test(lambda u: u.is_staff)
def check_product_name(request):
    """
    AJAX: /shop/check-name/?name=abc&exclude=<id>
    Trả về: {"ok": true, "exists": false}
    """
    name = (request.GET.get("name") or "").strip()
    exclude = request.GET.get("exclude")
    qs = Product.objects.all()
    if exclude and str(exclude).isdigit():
        qs = qs.exclude(pk=int(exclude))
    exists = bool(name) and qs.filter(name__iexact=name).exists()
    return JsonResponse({"ok": (bool(name) and not exists), "exists": exists})



from .models import Category, Product, ProductImage, ConsultationRequest, Order, OrderItem
@user_passes_test(lambda u: u.is_staff)
@require_POST
def consult_create_order(request, pk: int):
    """
    Tạo đơn NHÁP cho đúng khách của yêu cầu tư vấn pk, gồm đúng sản phẩm đó.
    Body: qty (mặc định 1), note (tuỳ chọn)
    """
    consult = get_object_or_404(ConsultationRequest.objects.select_related('user', 'product'), pk=pk)
    qty = request.POST.get('qty') or '1'
    try:
        qty = max(1, int(qty))
    except Exception:
        qty = 1

    order = Order.objects.create(
        user=consult.user,
        note=f'Từ yêu cầu tư vấn #{consult.pk} cho {consult.product.name}',
        status='draft'
    )
    OrderItem.objects.create(
        order=order,
        product=consult.product,
        quantity=qty,
        price=consult.product.price
    )
    order.recalc(save=True)

    msg = f'Đã tạo đơn #{order.pk} cho {consult.user.username}.'
    if _is_ajax(request):
        return JsonResponse({'ok': True, 'order_id': order.pk, 'url': order.get_absolute_url(), 'message': msg})
    messages.success(request, msg)
    return redirect(order.get_absolute_url())



@user_passes_test(lambda u: u.is_staff)
def order_detail(request, order_id: int):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product'),
        pk=order_id
    )
    return render(request, 'shop/order_detail.html', {'order': order})




from django.db.models import Count, Sum, F, Avg, DurationField, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce

# shop/views.py
# shop/views.py
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, F, Avg, DurationField, ExpressionWrapper
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from django.contrib.auth.models import User
import csv
import io
from datetime import datetime
try:
    import openpyxl
except Exception:
    openpyxl = None

from .models import (
    Product, Category, Order, OrderItem, PageView, ConsultationRequest
)  # Order/OrderItem/ConsultationRequest/PageView có sẵn. :contentReference[oaicite:4]{index=4}

def _staff(u): return u.is_staff

@user_passes_test(_staff)
def admin_reports(request):
    categories = Category.objects.all().order_by("name")
    suppliers = Product.objects.exclude(supplier="").values_list("supplier", flat=True).distinct().order_by("supplier")
    return render(request, "shop/admin_reports.html", {
        "categories": categories,
        "suppliers": suppliers
    })

from django.http import JsonResponse
from django.utils import timezone
from django.db.models import (
    Count, Sum, F, Avg, DurationField, DecimalField, ExpressionWrapper
)
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce
from django.contrib.auth.models import User
from .models import OrderItem, Category, Product, PageView, ConsultationRequest



from django.http import JsonResponse
from django.utils import timezone
from django.db.models import (
    Q, F, Count, Sum, Avg, DurationField, DecimalField, ExpressionWrapper
)
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, Coalesce
from django.contrib.auth.models import User
from .models import OrderItem, Category, Product, PageView, ConsultationRequest

def admin_reports_data(request):
    """
    JSON báo cáo cho dashboard admin:
      - users_by_period
      - visits_by_period
      - orders_by_supplier
      - orders_by_category
      - consult_by_status
      - consult_by_staff
      - consult_by_period
      - can_see_revenue (bool)

    Query params:
      date_from, date_to (YYYY-MM-DD, optional)
      group_by = day|week|month (default: day)
      supplier (optional, exact match)
      category_id (optional, int)
      fmt = csv|xlsx (optional, để xuất file)
      kind = users|visits|orders_by_supplier|orders_by_category|consult_by_status|consult_by_staff|consult_by_period
    """
    # ====== imports cục bộ cho export tránh thiếu ======
    import io, csv
    try:
        import openpyxl   # pip install openpyxl nếu muốn export xlsx
    except Exception:
        openpyxl = None

    from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
    from django.utils import timezone
    from django.db.models import (
        Q, F, Count, Sum, Avg, DurationField, DecimalField, ExpressionWrapper,
        Value, CharField
    )
    from django.db.models.functions import (
        TruncDate, TruncWeek, TruncMonth, Coalesce, Concat
    )
    from django.contrib.auth.models import User

    from .models import OrderItem, Category, Product, PageView, ConsultationRequest

    # ====== parse params ======
    df = request.GET.get("date_from")
    dt = request.GET.get("date_to")
    supplier = (request.GET.get("supplier") or "").strip()
    category_id = request.GET.get("category_id")
    group_by = (request.GET.get("group_by") or "day").lower()

    now = timezone.now()
    date_to = timezone.datetime.fromisoformat(dt) if dt else now
    date_from = timezone.datetime.fromisoformat(df) if df else (now - timezone.timedelta(days=30))
    if timezone.is_naive(date_from): date_from = timezone.make_aware(date_from)
    if timezone.is_naive(date_to):   date_to   = timezone.make_aware(date_to)

    # Chọn hàm group theo kỳ
    G = TruncDate
    if group_by == "week":
        G = TruncWeek
    elif group_by == "month":
        G = TruncMonth

    # Quyền xem doanh thu
    can_see_revenue = bool(getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False))

    # ====== Users mới theo kỳ ======
    users_qs = (
        User.objects.filter(date_joined__gte=date_from, date_joined__lt=date_to)
        .annotate(p=G("date_joined"))
        .values("p")
        .annotate(count=Count("id"))
        .order_by("p")
    )
    users_by_period = [
        {
            "period": (x["p"].isoformat() if hasattr(x["p"], "isoformat") else str(x["p"])),
            "count": x["count"]
        }
        for x in users_qs
    ]

    # ====== OrderItem base + filters ======
    items = (
        OrderItem.objects
        .filter(order__created_at__gte=date_from, order__created_at__lt=date_to)
        .select_related("product", "order", "product__category")
    )
    if supplier:
        items = items.filter(product__supplier__iexact=supplier)
    if category_id and str(category_id).isdigit():
        items = items.filter(product__category_id=int(category_id))

    # Tính line_total trước rồi mới Sum để tránh lỗi aggregate
    items = items.annotate(
        line_total=ExpressionWrapper(
            Coalesce(F("price"), 0) * Coalesce(F("quantity"), 0),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
    )

    # ====== Orders by supplier ======
    by_supplier_qs = (
        items.values("product__supplier")
        .annotate(
            orders=Count("id"),
            quantity=Sum("quantity"),
            revenue=Sum("line_total"),
        )
        .order_by("product__supplier")
    )
    orders_by_supplier = [
        {
            "supplier": r["product__supplier"] or "(khác/không rõ)",
            "orders": r["orders"] or 0,
            "quantity": int(r["quantity"] or 0),
            "revenue": float(r["revenue"] or 0) if can_see_revenue else None,
        }
        for r in by_supplier_qs
    ]

    # ====== Orders by category ======
    by_category_qs = (
        items.values("product__category__name")
        .annotate(
            orders=Count("id"),
            quantity=Sum("quantity"),
            revenue=Sum("line_total"),
        )
        .order_by("product__category__name")
    )
    orders_by_category = [
        {
            "category": r["product__category__name"] or "(khác)",
            "orders": r["orders"] or 0,
            "quantity": int(r["quantity"] or 0),
            "revenue": float(r["revenue"] or 0) if can_see_revenue else None,
        }
        for r in by_category_qs
    ]

    # ====== Lượt truy cập theo kỳ (sessions ~ ip + user_agent) ======
    visits_qs = (
        PageView.objects.filter(created_at__gte=date_from, created_at__lt=date_to)
        .annotate(p=G("created_at"))
        .annotate(k=Concat("ip", Value("|"), "user_agent", output_field=CharField()))
        .values("p")
        .annotate(views=Count("id"), sessions=Count("k", distinct=True))
        .order_by("p")
    )
    visits_by_period = [
        {
            "period": (x["p"].isoformat() if hasattr(x["p"], "isoformat") else str(x["p"])),
            "views": x["views"],
            "sessions": x["sessions"],
        }
        for x in visits_qs
    ]

    # ====== Báo cáo Tư vấn ======
    consult_base = ConsultationRequest.objects.filter(created_at__gte=date_from, created_at__lt=date_to)

    consult_by_status_qs = consult_base.values("status").annotate(count=Count("id")).order_by("status")
    consult_by_status = [{"status": c["status"], "count": c["count"]} for c in consult_by_status_qs]

    consult_by_staff_qs = (
        consult_base.values(staff=F("handled_by__username"))
        .annotate(count=Count("id"))
        .order_by("staff")
    )
    consult_by_staff = [{"staff": r["staff"] or "(chưa phân công)", "count": r["count"]} for r in consult_by_staff_qs]

    # TB thời gian xử lý (handled_at - created_at); chỉ tính bản ghi có handled_at
    handle_delta = ExpressionWrapper(F("handled_at") - F("created_at"), output_field=DurationField())
    consult_period_qs = (
        consult_base.annotate(p=G("created_at"))
        .values("p")
        .annotate(
            total=Count("id"),
            done=Count("id", filter=Q(status="done")),
            avg_secs=Avg(handle_delta),
        )
        .order_by("p")
    )
    consult_by_period = []
    for x in consult_period_qs:
        avg_seconds = x["avg_secs"].total_seconds() if x["avg_secs"] else None
        consult_by_period.append({
            "period": (x["p"].isoformat() if hasattr(x["p"], "isoformat") else str(x["p"])),
            "total": x["total"],
            "done": x["done"],
            "avg_seconds": avg_seconds,
        })

    # ====== Build JSON ======
    payload = {
        "users_by_period": users_by_period,
        "visits_by_period": visits_by_period,
        "orders_by_supplier": orders_by_supplier,
        "orders_by_category": orders_by_category,
        "consult_by_status": consult_by_status,
        "consult_by_staff": consult_by_staff,
        "consult_by_period": consult_by_period,
        "can_see_revenue": can_see_revenue,
    }

    # ====== Xuất CSV/XLSX nếu được yêu cầu ======
    fmt = (request.GET.get("fmt") or "").lower().strip()
    kind = (request.GET.get("kind") or "").lower().strip()

    def _rows_and_headers(kind: str):
        if kind == "users":
            return users_by_period, ["period", "count"]
        if kind == "visits":
            return visits_by_period, ["period", "views", "sessions"]
        if kind == "orders_by_supplier":
            return orders_by_supplier, ["supplier", "orders", "quantity", "revenue"]
        if kind == "orders_by_category":
            return orders_by_category, ["category", "orders", "quantity", "revenue"]
        if kind == "consult_by_status":
            return consult_by_status, ["status", "count"]
        if kind == "consult_by_staff":
            return consult_by_staff, ["staff", "count"]
        if kind == "consult_by_period":
            return consult_by_period, ["period", "total", "done", "avg_seconds"]
        return None, None

    if fmt in {"csv", "xlsx"} and kind:
        rows, headers = _rows_and_headers(kind)
        if rows is None:
            return JsonResponse({"error": "invalid kind"}, status=400)

        if fmt == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(headers)
            for r in rows:
                w.writerow([r.get(h, "") for h in headers])
            out = buf.getvalue().encode("utf-8-sig")
            resp = HttpResponse(out, content_type="text/csv; charset=UTF-8")
            resp["Content-Disposition"] = f'attachment; filename="{kind}-{timezone.now():%Y%m%d%H%M%S}.csv"'
            return resp

        if fmt == "xlsx":
            if openpyxl is None:
                return JsonResponse({"error": "openpyxl not installed"}, status=400)
            wb = openpyxl.Workbook()
            ws = wb.active; ws.title = kind
            ws.append(headers)
            for r in rows:
                ws.append([r.get(h, "") for h in headers])
            bio = io.BytesIO()
            wb.save(bio)
            resp = HttpResponse(bio.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            resp["Content-Disposition"] = f'attachment; filename="{kind}-{timezone.now():%Y%m%d%H%M%S}.xlsx"'
            return resp

    return JsonResponse(payload)






@user_passes_test(_staff)
def admin_reports_export(request):
    """
    Xuất CSV/XLSX cho 1 'dataset':
      kind=users|visits|supplier|category|consult_status|consult_staff|consult_period
      format=csv|xlsx
      (dùng chung tham số date_from/date_to/supplier/category_id/group_by như /data)
    """
    kind = request.GET.get("kind") or "supplier"
    fmt  = (request.GET.get("format") or "csv").lower()
    # gọi lại data JSON để tái sử dụng logic & phân quyền
    data_resp = admin_reports_data(request)
    if data_resp.status_code != 200:
        return data_resp
    data = data_resp.json()

    # map dataset
    map_kind = {
        "users": ("users_by_period", ["period","count"]),
        "visits": ("visits_by_period", ["period","views","sessions"]),
        "supplier": ("orders_by_supplier", ["supplier","orders","quantity"] + (["revenue"] if data.get("can_see_revenue") else [])),
        "category": ("orders_by_category", ["category","orders","quantity"] + (["revenue"] if data.get("can_see_revenue") else [])),
        "consult_status": ("consult_by_status", ["status","count"]),
        "consult_staff": ("consult_by_staff", ["staff","count"]),
        "consult_period": ("consult_by_period", ["period","total","done","avg_seconds"]),
    }
    if kind not in map_kind:
        return JsonResponse({"error": "invalid kind"}, status=400)
    key, headers = map_kind[kind]
    rows = data.get(key, [])

    # CSV
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        for r in rows:
            writer.writerow([r.get(h, "") for h in headers])
        out = buf.getvalue().encode("utf-8-sig")
        resp = HttpResponse(out, content_type="text/csv; charset=UTF-8")
        resp["Content-Disposition"] = f'attachment; filename="{kind}-{datetime.now():%Y%m%d%H%M%S}.csv"'
        return resp

    # XLSX
    if fmt == "xlsx":
        if openpyxl is None:
            return JsonResponse({"error":"openpyxl not installed"}, status=400)
        wb = openpyxl.Workbook()
        ws = wb.active; ws.title = kind
        ws.append(headers)
        for r in rows:
            ws.append([r.get(h, "") for h in headers])
        bio = io.BytesIO()
        wb.save(bio)
        resp = HttpResponse(bio.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="{kind}-{datetime.now():%Y%m%d%H%M%S}.xlsx"'
        return resp

    return JsonResponse({"error": "invalid format"}, status=400)



# shop/forms.py (thêm vào cuối file)
# class ServicePlanForm(forms.ModelForm):
#     class Meta:
#         model = ServicePlan
#         fields = ("product", "name", "term", "custom_days", "price", "is_active", "ordering")
#         widgets = {
#             "custom_days": forms.NumberInput(attrs={"min": "0"}),
#             "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
#             "ordering": forms.NumberInput(attrs={"min": "0"}),
#         }

#     def clean(self):
#         cleaned_data = super().clean()
#         term = cleaned_data.get("term")
#         custom_days = cleaned_data.get("custom_days", 0)
        
#         if term == ServicePlan.Term.CUSTOM and custom_days <= 0:
#             raise forms.ValidationError("Vui lòng nhập số ngày cho gói tùy chỉnh.")
        
#         if term != ServicePlan.Term.CUSTOM and custom_days > 0:
#             cleaned_data["custom_days"] = 0  # Reset nếu không phải custom
            
#         return cleaned_data
    
    
# shop/views.py (thêm các view mới)
@user_passes_test(lambda u: u.is_staff)
def admin_serviceplan_create(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        form = ServicePlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.product = product
            plan.save()
            messages.success(request, "Đã tạo gói dịch vụ thành công.")
            return redirect("shop:product_detail", slug=product.slug)
    else:
        form = ServicePlanForm(initial={"product": product})
    return render(request, "shop/admin_serviceplan_form.html", {
        "form": form, 
        "product": product,
        "title": f"Thêm gói dịch vụ cho {product.name}"
    })

@user_passes_test(lambda u: u.is_staff)
def admin_serviceplan_update(request, pk):
    plan = get_object_or_404(ServicePlan, pk=pk)
    if request.method == "POST":
        form = ServicePlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật gói dịch vụ.")
            return redirect("shop:product_detail", slug=plan.product.slug)
    else:
        form = ServicePlanForm(instance=plan)
    return render(request, "shop/admin_serviceplan_form.html", {
        "form": form,
        "product": plan.product,
        "title": f"Sửa gói dịch vụ: {plan.name}"
    })

@user_passes_test(lambda u: u.is_staff)
def admin_serviceplan_delete(request, pk):
    plan = get_object_or_404(ServicePlan, pk=pk)
    product_slug = plan.product.slug
    if request.method == "POST":
        plan.delete()
        messages.success(request, "Đã xóa gói dịch vụ.")
        return redirect("shop:product_detail", slug=product_slug)
    return render(request, "shop/admin_serviceplan_confirm_delete.html", {"plan": plan})



# shop/views.py (thêm API)
from django.http import JsonResponse

def api_product_plans(request, product_id):
    """API trả về danh sách gói dịch vụ của sản phẩm"""
    product = get_object_or_404(Product, pk=product_id)
    plans = ServicePlan.objects.filter(product=product, is_active=True).order_by("ordering", "id")
    
    data = []
    for plan in plans:
        data.append({
            "id": plan.id,
            "name": plan.name,
            "term": plan.get_term_display(),
            "duration_days": plan.duration_days(),
            "price": float(plan.price),
            "description": f"{plan.name} - {plan.get_term_display()}"
        })
    
    return JsonResponse({"plans": data})





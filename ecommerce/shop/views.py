# shop/views.py
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm, ProductForm, ProductImagesForm
from .models import Category, Product, ProductImage


# Prefetch chỉ lấy ảnh có file để tránh link ảnh bị vỡ
VALID_IMAGES_PREFETCH = Prefetch(
    "images",
    queryset=ProductImage.objects.filter(image__isnull=False).exclude(image=""),
)

# ---------- Public ----------

# shop/views.py
from django.shortcuts import render, get_object_or_404
from .models import Product, Category
# 👉 import thêm
from news.models import News

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.all()
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # 👉 thêm đoạn lấy tin tức mới nhất
    latest_news = News.objects.order_by("-published_at")[:3]

    return render(request, "shop/product_list.html", {
        "products": products,
        "categories": categories,
        "active_category": category,
        "latest_news": latest_news,  # truyền sang template
    })



def product_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = (
        category.products.all()
        .select_related("category")
        .prefetch_related(VALID_IMAGES_PREFETCH)
    )
    categories = Category.objects.all()
    return render(
        request,
        "shop/product_list.html",
        {
            "products": products,
            "categories": categories,
            "active_category": category,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related(VALID_IMAGES_PREFETCH),
        slug=slug,
    )
    return render(request, "shop/product_detail.html", {"product": product})


# ---------- Admin (staff only) ----------

# ... các import giữ nguyên
from django.contrib import messages
from django.shortcuts import redirect

@user_passes_test(lambda u: u.is_staff)
def admin_product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        images_form = ProductImagesForm()
        if form.is_valid():
            product = form.save()
            for f in request.FILES.getlist("images"):
                ProductImage.objects.create(product=product, image=f)

            messages.success(request, "Đã tạo sản phẩm thành công.")
            return redirect("shop:product_list")
        else:
            messages.error(request, "Dữ liệu chưa hợp lệ, vui lòng kiểm tra.")
    else:
        form = ProductForm()
        images_form = ProductImagesForm()

    return render(request, "shop/admin_product_form.html",
                  {"form": form, "images_form": images_form})



@user_passes_test(lambda u: u.is_staff)
def admin_product_update(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related(VALID_IMAGES_PREFETCH), pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        images_form = ProductImagesForm()          # ⬅️ KHÔNG bind
        if form.is_valid():                        # ⬅️ Chỉ validate form chính
            form.save()

            # Xóa ảnh phụ được tick
            to_delete_ids = request.POST.getlist("delete_images")
            if to_delete_ids:
                ProductImage.objects.filter(id__in=to_delete_ids, product=product).delete()

            # Thêm ảnh mới (nếu có)
            for f in request.FILES.getlist("images"):
                ProductImage.objects.create(product=product, image=f)

            messages.success(request, "Đã cập nhật sản phẩm.")
            return redirect("shop:product_detail", slug=product.slug)
        else:
            messages.error(request, "Dữ liệu chưa hợp lệ, vui lòng kiểm tra.")
    else:
        form = ProductForm(instance=product)
        images_form = ProductImagesForm()

    return render(request, "shop/admin_product_form.html", {
        "form": form, "images_form": images_form, "product": product, "is_edit": True
    })



@user_passes_test(lambda u: u.is_staff)
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        name = product.name
        product.delete()  # CASCADE xóa cả ProductImage
        messages.success(request, f"Đã xoá sản phẩm: {name}")
        return redirect("shop:product_list")
    return render(
        request, "shop/admin_product_confirm_delete.html", {"product": product}
    )


@user_passes_test(lambda u: u.is_staff)
def admin_category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã tạo danh mục.")
            return redirect("shop:product_list")
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
            return redirect("shop:product_list")
    else:
        form = CategoryForm(instance=category)
    return render(
        request,
        "shop/admin_category_form.html",
        {"form": form, "category": category, "is_edit": True},
    )


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



# shop/views.py (thêm import)
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.admin.views.decorators import staff_member_required
from .models import Product

@require_GET
@staff_member_required
def check_product_name(request):
    """
    ?name=Gói dv 1&exclude=<id-sản-phẩm-đang-sửa>
    Trả về: {"ok": true/false, "exists": true/false}
    """
    name = (request.GET.get("name") or "").strip()
    exclude = request.GET.get("exclude")
    qs = Product.objects.all()
    if exclude and exclude.isdigit():
        qs = qs.exclude(pk=int(exclude))
    exists = bool(name) and qs.filter(name__iexact=name).exists()
    return JsonResponse({"ok": (bool(name) and not exists), "exists": exists})





# news/views.py
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .forms import NewsForm
from .models import News

is_staff = user_passes_test(lambda u: u.is_staff)

# Public
def news_list(request):
    # Bỏ filter is_published
    qs = News.objects.all().order_by('-published_at')
    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "news/list.html", {
        "news_list": page_obj.object_list,
        "is_paginated": page_obj.has_other_pages(),
        "paginator": paginator,
        "page_obj": page_obj,
    })


def news_detail(request, slug):
    # Bỏ filter is_published
    item = get_object_or_404(News, slug=slug)
    return render(request, "news/detail.html", {"item": item})



# Admin
@is_staff
def admin_news_create(request):
    if request.method == "POST":
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            for k in ("crop_x", "crop_y", "crop_w", "crop_h"):
                setattr(obj, k, int(form.cleaned_data.get(k) or 0))
            if request.user.is_authenticated:
                obj.author = request.user
            obj.save()
            messages.success(request, "Đăng bài thành công.")
            return redirect("news:list")
    else:
        form = NewsForm()
    return render(request, "news/admin_news_form.html", {"form": form})

@is_staff
def admin_news_edit(request, pk):
    item = get_object_or_404(News, pk=pk)
    if request.method == "POST":
        form = NewsForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            for k in ("crop_x", "crop_y", "crop_w", "crop_h"):
                setattr(obj, k, int(form.cleaned_data.get(k) or 0))
            obj.save()
            messages.success(request, "Cập nhật thành công.")
            return redirect("news:detail", slug=obj.slug)
    else:
        form = NewsForm(instance=item)
    return render(request, "news/admin_news_form.html", {"form": form, "item": item})

@is_staff
def admin_news_delete(request, pk):
    item = get_object_or_404(News, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Đã xoá bài viết.")
        return redirect("news:list")
    return render(request, "news/confirm_delete.html", {"item": item})

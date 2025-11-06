# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    RegisterForm,
    UserNamesForm,
    ProfileAvatarForm,
    ProfilePhotosForm,
)
from .models import Profile, ProfileImage


# ----------------------------
# Đăng ký tài khoản
# ----------------------------
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, redirect
from .forms import RegisterForm
from .models import Profile

def register(request):
    if request.user.is_authenticated:
        messages.info(request, "Bạn đã đăng nhập.")
        return redirect("shop:product_list")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = (form.cleaned_data["username"] or "").strip()
            email = (form.cleaned_data["email"] or "").strip()

            # Kiểm tra trùng (không ném exception)
            has_dup = False
            if User.objects.filter(username__iexact=username).exists():
                form.add_error("username", "Tên đăng nhập đã tồn tại.")
                has_dup = True
            if User.objects.filter(email__iexact=email).exists():
                form.add_error("email", "Email đã tồn tại.")
                has_dup = True

            if has_dup:
                messages.error(request, "Vui lòng sửa các lỗi bên dưới.")
            else:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=form.cleaned_data["password"],
                    )
                    profile, _ = Profile.objects.get_or_create(user=user)
                    phone = form.cleaned_data.get("phone")
                    if phone:
                        profile.phone = phone
                        profile.save()

                login(request, user)
                messages.success(request, "Tạo tài khoản thành công! 🎉")
                return redirect("shop:product_list")   # về trang chủ
        # form không hợp lệ sẽ rơi xuống render bên dưới
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})






# ----------------------------
# Đăng nhập
# ----------------------------
def user_login(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next") or reverse("shop:product_list")
            return redirect(next_url)
        messages.error(request, "Sai tên đăng nhập hoặc mật khẩu.")

    return render(request, "accounts/login.html")


# ----------------------------
# Đăng xuất
# ----------------------------
@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "Bạn đã đăng xuất.")
    return redirect("shop:product_list")


# ----------------------------
# Hồ sơ người dùng
# - Cho phép đổi Họ/Tên và Avatar
# - Cho phép thêm NHIỀU ảnh vào thư viện (gallery)
# - KHÔNG cho đổi email và SĐT (không có trong form)
# ----------------------------
@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        name_form = UserNamesForm(request.POST, instance=request.user)
        avatar_form = ProfileAvatarForm(request.POST, request.FILES, instance=profile_obj)
        photos_form = ProfilePhotosForm(request.POST, request.FILES)

        if name_form.is_valid() and avatar_form.is_valid() and photos_form.is_valid():
            with transaction.atomic():
                # LƯU họ tên
                name_form.save()

                # LƯU avatar
                avatar_form.save()

                # THÊM nhiều ảnh gallery
                for f in request.FILES.getlist("photos"):
                    ProfileImage.objects.create(profile=profile_obj, image=f)

            messages.success(request, "Cập nhật hồ sơ thành công.")
            return redirect("accounts:profile")
        else:
            messages.error(request, "Có lỗi, vui lòng kiểm tra lại biểu mẫu.")
    else:
        name_form = UserNamesForm(instance=request.user)
        avatar_form = ProfileAvatarForm(instance=profile_obj)
        photos_form = ProfilePhotosForm()

    context = {
        "name_form": name_form,
        "avatar_form": avatar_form,
        "photos_form": photos_form,
        # Hiển thị read-only (KHÔNG cho sửa):
        "email": request.user.email,
        "phone": profile_obj.phone or "",
        # Thư viện ảnh
        "photos": profile_obj.photos.all().order_by("-uploaded_at"),
    }
    return render(request, "accounts/profile.html", context)


# ----------------------------
# Xoá ảnh trong thư viện (chỉ chủ ảnh)
# ----------------------------
@login_required
def delete_profile_photo(request, pk: int):
    photo = get_object_or_404(ProfileImage, pk=pk, profile__user=request.user)
    photo.delete()
    messages.success(request, "Đã xoá ảnh.")
    return redirect("accounts:profile")




# accounts/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django import forms
from .models import Profile

class AdminUserForm(forms.ModelForm):
    """
    Form cho admin chỉnh: Họ, Tên, Email, (tùy superuser) is_staff, is_active.
    Truyền can_promote=True để hiển thị is_staff.
    """
    def __init__(self, *args, can_promote=False, **kwargs):
        super().__init__(*args, **kwargs)
        # Email unique theo user (exclude chính mình)
        self.fields["email"].required = True
        if not can_promote and "is_staff" in self.fields:
            self.fields.pop("is_staff")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "is_active", "is_staff")
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Họ"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Tên"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@domain.com"}),
        }
        labels = {
            "first_name": "Họ",
            "last_name": "Tên",
            "email": "Email",
            "is_active": "Hoạt động",
            "is_staff": "Quyền Staff",
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email


class AdminProfileForm(forms.ModelForm):
    """Form chỉnh SĐT & Avatar trong Profile."""
    class Meta:
        model = Profile
        fields = ("phone", "avatar")
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "Số điện thoại"}),
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
        }
        labels = {"phone": "Số điện thoại", "avatar": "Ảnh đại diện"}

@staff_member_required
def admin_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = Profile.get_or_create(user=user) if not hasattr(user, "profile") else (user.profile, None)
    if request.method == "POST":
        uf = AdminUserForm(request.POST, instance=user)
        pf = AdminProfileForm(request.POST, request.FILES, instance=profile)
        if uf.is_valid() and pf.is_valid():
            uf.save(); pf.save()
            messages.success(request, "Cập nhật thành công.")
            return redirect("accounts:admin_user_edit", pk=user.pk)
    else:
        uf = AdminUserForm(instance=user)
        pf = AdminProfileForm(instance=profile)
    return render(request, "accounts/admin_user_edit.html", {"uf": uf, "pf": pf, "obj": user})




#_______________
# accounts/views.py
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AdminUserForm, AdminProfileForm
from .models import Profile


@staff_member_required
def admin_user_list(request):
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.all().select_related("profile").order_by("username")
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(profile__phone__icontains=q)
        )
    paginator = Paginator(qs, 12)
    users = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/admin_user_list.html", {"users": users, "q": q})


@staff_member_required
def admin_user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = Profile.objects.get_or_create(user=user)

    can_promote = request.user.is_superuser
    if request.method == "POST":
        uf = AdminUserForm(request.POST, instance=user, can_promote=can_promote)
        pf = AdminProfileForm(request.POST, request.FILES, instance=profile)
        if uf.is_valid() and pf.is_valid():
            uf.save()
            pf.save()
            messages.success(request, "Cập nhật người dùng thành công.")
            return redirect("accounts:admin_user_edit", pk=user.pk)
        else:
            messages.error(request, "Vui lòng kiểm tra lại các lỗi.")
    else:
        uf = AdminUserForm(instance=user, can_promote=can_promote)
        pf = AdminProfileForm(instance=profile)

    return render(
        request,
        "accounts/admin_user_edit.html",
        {"uf": uf, "pf": pf, "obj": user},
    )


@staff_member_required
@require_POST
def admin_user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "Không thể vô hiệu hoá chính bạn.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(
            request, f"Đã {'kích hoạt' if user.is_active else 'vô hiệu hoá'} tài khoản {user.username}."
        )
    return redirect("accounts:admin_user_list")

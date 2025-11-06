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
# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse

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
            password = form.cleaned_data["password1"]
            phone = (form.cleaned_data.get("phone") or "").strip()

            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                )
                # Profile đã được tạo bởi signal; chỉ cần gán phone nếu có
                if phone:
                    user.profile.phone = phone
                    user.profile.save(update_fields=["phone"])

            login(request, user)
            messages.success(request, "Tạo tài khoản thành công! 🎉")
            return redirect("shop:product_list")
        else:
            messages.error(request, "Vui lòng sửa các lỗi bên dưới.")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})






# ----------------------------
# Đăng nhập
# ----------------------------
# accounts/views.py
# accounts/views.py
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import render, redirect
from django.urls import reverse, NoReverseMatch
from django.conf import settings

def _try_reverse(candidates):
    """Trả về URL đầu tiên reverse được trong danh sách tên URL; không có thì None."""
    for name in candidates:
        try:
            return reverse(name)
        except NoReverseMatch:
            continue
    return None

def user_login(request):
    next_url = request.GET.get('next') or request.POST.get('next') or settings.LOGIN_REDIRECT_URL

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(next_url)
    else:
        form = AuthenticationForm(request)

    # ✅ KHÔNG dùng resolver_match nữa
    password_reset_url = _try_reverse(['accounts:password_reset', 'password_reset'])

    ctx = {
        'form': form,
        'password_reset_url': password_reset_url,
    }
    return render(request, 'accounts/login.html', ctx)

def register(request):
    # Nếu có RegisterForm riêng thì import vào và thay FormClass
    FormClass = UserCreationForm

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or settings.LOGIN_REDIRECT_URL
            return redirect(next_url)
    else:
        form = FormClass()

    return render(request, 'accounts/register.html', {'form': form})

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


def _safe_avatar_url(user):
    try:
        av = getattr(getattr(user, "profile", None), "avatar", None)
        return av.url if av and hasattr(av, "url") else ""
    except Exception:
        return ""


# ---------- Helpers cho Phone ----------
import re

_PHONE_ALLOWED_RE = re.compile(r"^[0-9+\s\-\.\(\)]+$")


def normalize_phone(raw: str) -> str:
    """
    Chuẩn hoá SĐT:
    - Giữ dấu + nếu đứng đầu; còn lại bỏ mọi ký tự không phải số.
    - Bỏ khoảng trắng, -, ., (, ).
    - Ví dụ: "+84 912-345-678" -> "+84912345678"
             "0912 345 678"   -> "0912345678"
    """
    if not raw:
        return ""
    raw = raw.strip()

    plus = raw.startswith("+")
    # loại bỏ tất cả ký tự không phải 0-9
    digits = re.sub(r"[^0-9]", "", raw)

    # giữ + ở đầu nếu ban đầu có
    return ("+" + digits) if plus and digits else digits


def validate_phone(raw: str):
    """
    Trả về (ok: bool, message: str).
    Quy tắc:
      - Chỉ cho phép các ký tự: 0-9, +, khoảng trắng, -, ., (, )
      - Sau chuẩn hoá, số chữ số (bỏ +) phải từ 8..15 là hợp lý (tuỳ chỉnh).
    """
    if not raw:
        return False, "Vui lòng nhập số điện thoại."

    if not _PHONE_ALLOWED_RE.match(raw):
        return False, "Số điện thoại chứa ký tự không hợp lệ."

    normalized = normalize_phone(raw)

    # số chữ số (không tính +)
    digits_only = normalized[1:] if normalized.startswith("+") else normalized

    if not (8 <= len(digits_only) <= 15):
        return False, "Số điện thoại phải có từ 8 đến 15 chữ số."

    return True, ""


def phone_exists_for_other_user(user, normalized_phone: str) -> bool:
    """
    Kiểm tra trùng SĐT trên:
      - Profile.phone của người khác
      - (Tuỳ dự án) User.phone nếu tồn tại field đó
    """
    # Trùng ở Profile.phone
    if hasattr(Profile, "phone"):
        if Profile.objects.filter(phone=normalized_phone).exclude(user=user).exists():
            return True

    # Trùng ở User.phone nếu dự án có field này
    if hasattr(user.__class__, "phone"):
        if user.__class__.objects.filter(phone=normalized_phone).exclude(pk=user.pk).exists():
            return True

    return False

# accounts/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.templatetags.static import static  # ⬅ cần cho avatar_fallback
from .forms import UserNamesForm, ProfileAvatarForm
from cart.models import Order

def _safe_avatar_url(user):
    """Trả về URL avatar nếu có, nếu lỗi thì chuỗi rỗng."""
    try:
        av = getattr(getattr(user, "profile", None), "avatar", None)
        return av.url if av and hasattr(av, "url") else ""
    except Exception:
        return ""

@login_required
@transaction.atomic
def profile(request):
    user = request.user

    # --- Forms mặc định ---
    name_form = UserNamesForm(instance=user)
    avatar_form = ProfileAvatarForm(instance=user.profile)

    if request.method == "POST":
        action = request.POST.get("action")

        # ======= AVATAR =======
        if action == "save_avatar":
            avatar_form = ProfileAvatarForm(
                request.POST, request.FILES, instance=user.profile
            )
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, "Ảnh đại diện đã được cập nhật.")
                return redirect("accounts:profile")
            else:
                messages.error(request, "Không thể cập nhật ảnh đại diện. Vui lòng thử lại.")

        # ======= PROFILE (Họ tên + SĐT nếu CHƯA có) =======
        elif action == "save_profile":
            name_form = UserNamesForm(request.POST, instance=user)
            post_phone_raw = (request.POST.get("phone") or "").strip()

            # Kiểm tra form họ tên trước
            if not name_form.is_valid():
                messages.error(request, "Dữ liệu không hợp lệ, vui lòng kiểm tra lại.")
            else:
                # Lưu họ tên
                name_form.save()

                # Chỉ xử lý phone nếu người dùng CHƯA có sđt trước đó và form có ô nhập (theo template)
                profile_obj = getattr(user, "profile", None)
                current_phone = ""
                if profile_obj and hasattr(profile_obj, "phone") and profile_obj.phone:
                    current_phone = profile_obj.phone
                elif hasattr(user, "phone") and user.phone:
                    current_phone = user.phone

                # Nếu chưa có phone, cho phép set mới (và validate + check trùng)
                if not (current_phone or "").strip() and post_phone_raw:
                    ok, msg = validate_phone(post_phone_raw)
                    if not ok:
                        messages.error(request, msg)
                        # rollback phần họ tên? tuỳ, ở đây vẫn cho lưu họ tên nhưng báo lỗi SĐT
                        return redirect("accounts:profile")

                    normalized = normalize_phone(post_phone_raw)

                    if phone_exists_for_other_user(user, normalized):
                        messages.error(request, "Số điện thoại đã được sử dụng")
                        return redirect("accounts:profile")

                    # Lưu phone vào Profile nếu có field, ngược lại lưu vào User (nếu có)
                    if profile_obj and hasattr(profile_obj, "phone"):
                        profile_obj.phone = normalized
                        profile_obj.save(update_fields=["phone"])
                    elif hasattr(user, "phone"):
                        user.phone = normalized
                        user.save(update_fields=["phone"])

                messages.success(request, "Cập nhật thông tin cá nhân thành công.")
                return redirect("accounts:profile")

        # Nếu POST không khớp action: bỏ qua

    # --- Lịch sử đơn hàng ---
    qs = (
        Order.objects.filter(user=user)
        .prefetch_related("items__product")
        .order_by("-created_at")
    )

    status = (request.GET.get("status") or "").upper().strip()
    valid_statuses = {s for s, _ in Order.Status.choices}
    if status in valid_statuses:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 10)
    page = request.GET.get("page") or 1
    orders = paginator.get_page(page)

    # Hiển thị phone ưu tiên ở Profile > User
    prof_phone = getattr(getattr(user, "profile", None), "phone", "") or ""
    user_phone = getattr(user, "phone", "") or ""
    phone_display = prof_phone or user_phone

    context = {
        "name_form": name_form,
        "avatar_form": avatar_form,
        "email": getattr(user, "email", "") or "",
        "phone": phone_display,
        "orders": orders,
        "current_status": status,
        "all_statuses": Order.Status.choices,
        "avatar_url": _safe_avatar_url(user),
        "avatar_fallback": static("img/placeholder-avatar.png"),
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

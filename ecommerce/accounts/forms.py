# accounts/forms.py
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile
import re


# ---------- Widgets ----------
class MultiFileInput(forms.ClearableFileInput):
    """Cho phép chọn nhiều file (dùng cho gallery)."""
    allow_multiple_selected = True


# ---------- Đăng ký tài khoản ----------
class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={"placeholder": "username"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"placeholder": "email@domain.com"})
    )
    phone = forms.CharField(
        label="Số điện thoại",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "SĐT"})
    )
    password1 = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"})
    )
    password2 = forms.CharField(
        label="Xác nhận mật khẩu",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"})
    )

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Tên đăng nhập đã tồn tại.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email đã được sử dụng.")
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not re.fullmatch(r"^\+?\d{9,15}$", phone):
            raise ValidationError("SĐT không hợp lệ (9–15 chữ số).")
        return phone

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password1"), cd.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Mật khẩu xác nhận không khớp.")
        return cd


# ---------- Đổi họ tên trong trang hồ sơ ----------
class UserNamesForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name")
        labels = {"first_name": "Họ", "last_name": "Tên"}
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Họ"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Tên"}),
        }


# ---------- Đổi avatar trong trang hồ sơ ----------
class ProfileAvatarForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("avatar",)
        labels = {"avatar": "Ảnh đại diện"}
        widgets = {
            "avatar": forms.FileInput(attrs={"accept": "image/*"})
        }


# ---------- Thêm nhiều ảnh vào thư viện trong trang hồ sơ ----------
class ProfilePhotosForm(forms.Form):
    photos = forms.FileField(
        label="Ảnh bổ sung",
        required=False,
        widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*"})
    )


# ---------- FORM cho trang QUẢN LÝ USER (Admin/Staff) ----------
class AdminUserForm(forms.ModelForm):
    """
    Chỉnh sửa: Họ, Tên, Email, is_active và (nếu superuser) is_staff.
    Truyền tham số can_promote=True ở __init__ để hiển thị is_staff.
    """
    def __init__(self, *args, can_promote=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        if not can_promote and "is_staff" in self.fields:
            # Ẩn field is_staff với non-superuser
            self.fields.pop("is_staff")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "is_active", "is_staff")
        labels = {
            "first_name": "Họ",
            "last_name": "Tên",
            "email": "Email",
            "is_active": "Hoạt động",
            "is_staff": "Quyền Staff",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Họ"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Tên"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@domain.com"}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Email này đã được sử dụng.")
        return email


class AdminProfileForm(forms.ModelForm):
    """Chỉnh sửa SĐT & Avatar của user trong Profile."""
    class Meta:
        model = Profile
        fields = ("phone", "avatar")
        labels = {"phone": "Số điện thoại", "avatar": "Ảnh đại diện"}
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "SĐT"}),
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
        }

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not re.fullmatch(r"^\+?\d{9,15}$", phone):
            raise ValidationError("SĐT không hợp lệ (9–15 chữ số).")
        return phone

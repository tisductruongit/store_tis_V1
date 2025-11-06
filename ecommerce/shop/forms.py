# shop/forms.py (rewritten)
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from django import forms
from django.core.exceptions import ValidationError

from .models import Category, Product, ServicePlan


# ===================== Helpers =====================

def _slugify_vn(text: str) -> str:
    """'Gói dịch vụ 1' -> 'goi-dich-vu-1' (ASCII slug)"""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    return (text.strip("-").lower()) or "item"


def _to_decimal_human(num_input) -> Decimal:
    """Chuyển chuỗi tiền tệ người dùng nhập thành Decimal.
    Hỗ trợ các kiểu: '12.345,67' (VN/EU) hoặc '12,345.67' (US) hoặc '12345.67'/'12345'.
    """
    if isinstance(num_input, (int, float, Decimal)):
        try:
            return Decimal(str(num_input))
        except InvalidOperation as e:
            raise ValidationError("Giá trị số không hợp lệ.") from e

    s = (num_input or "").strip()
    if not s:
        return Decimal("0")

    # Nếu có cả '.' và ',' thì đoán định dạng theo ký tự cuối cùng xuất hiện
    if "." in s and "," in s:
        last_dot = s.rfind(".")
        last_com = s.rfind(",")
        if last_com > last_dot:
            # VN/EU: dấu cuối là ',' -> là dấu thập phân
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            # US: dấu cuối là '.' -> là dấu thập phân
            s = s.replace(",", "")
    else:
        # Chỉ có một loại
        if s.count(",") == 1 and s.count(".") == 0:
            # Giả định ',' là dấu thập phân
            s = s.replace(",", ".")
        elif s.count(".") == 1 and s.count(",") == 0:
            # '.' có thể là thập phân (US) -> giữ nguyên
            pass
        elif s.count(",") > 1 and s.count(".") == 0:
            # Nhiều dấu ',' -> chắc là phân tách nghìn kiểu VN
            s = s.replace(",", "")
        elif s.count(".") > 1 and s.count(",") == 0:
            # Nhiều dấu '.' -> chắc là phân tách nghìn kiểu US
            s = s.replace(".", "")

    try:
        return Decimal(s)
    except InvalidOperation as e:
        raise ValidationError("Giá trị số không hợp lệ.") from e


# ===================== Forms =====================

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "is_active", "ordering")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Tên danh mục"}),
            "slug": forms.TextInput(attrs={"placeholder": "(để trống để tự tạo)"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "ordering": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        name = self.cleaned_data.get("name") or ""
        return slug or _slugify_vn(name)


class ProductForm(forms.ModelForm):
    price = forms.CharField()
    sale_price = forms.CharField(required=False)

    class Meta:
        model = Product
        fields = (
            "category",
            "name",
            "slug",
            "sku",
            "price",
            "sale_price",
            "stock",
            "supplier",
            "short_description",
            "description",
            "image",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Tên sản phẩm"}),
            "slug": forms.TextInput(attrs={"placeholder": "(để trống để tự tạo)"}),
            "sku": forms.TextInput(attrs={"placeholder": "SKU (nếu có)"}),
            "stock": forms.NumberInput(attrs={"min": 0}),
            "supplier": forms.TextInput(attrs={"placeholder": "Nhà cung cấp"}),
            "short_description": forms.Textarea(attrs={"rows": 2}),
            "description": forms.Textarea(attrs={"rows": 6}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        name = self.cleaned_data.get("name") or ""
        return slug or _slugify_vn(name)

    def clean_price(self):
        return _to_decimal_human(self.cleaned_data.get("price"))

    def clean_sale_price(self):
        raw = self.cleaned_data.get("sale_price")
        if raw in (None, ""):
            return None
        return _to_decimal_human(raw)

    def clean(self):
        cleaned = super().clean()
        price: Decimal = cleaned.get("price") or Decimal("0")
        sale: Decimal | None = cleaned.get("sale_price")
        if sale is not None and sale > price:
            self.add_error("sale_price", "Giá khuyến mãi không được lớn hơn giá gốc.")
        return cleaned

# Cho phép chọn nhiều file
class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True



class ProductImagesForm(forms.Form):
    images = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={"multiple": True})
    )

    def clean_images(self):
        files = self.files.getlist("images")
        if not files:
            return None
        for f in files:
            # Giới hạn kích thước và định dạng cơ bản
            if f.size > 5 * 1024 * 1024:
                raise ValidationError("Mỗi ảnh tối đa 5MB.")
            if not (getattr(f, "content_type", "").startswith("image/")):
                raise ValidationError("Chỉ được tải lên tệp hình ảnh.")
        return files



class ServicePlanForm(forms.ModelForm):
    price = forms.CharField()

    class Meta:
        model = ServicePlan
        fields = [
            "product",
            "name",
            "term",
            "custom_days",
            "price",
            "is_active",
            "ordering",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Tên gói"}),
            "custom_days": forms.NumberInput(attrs={"min": 0}),
            "ordering": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_price(self):
        return _to_decimal_human(self.cleaned_data.get("price"))

    def clean(self):
        cleaned = super().clean()
        term = cleaned.get("term")
        custom_days = int(cleaned.get("custom_days") or 0)
        if term == ServicePlan.Term.CUSTOM and custom_days <= 0:
            self.add_error("custom_days", "Vui lòng nhập số ngày cho gói tùy chỉnh.")
        if term != ServicePlan.Term.CUSTOM:
            cleaned["custom_days"] = 0
        return cleaned



# shop/forms.py
class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)
    plan = forms.ModelChoiceField(
        queryset=ServicePlan.objects.none(), required=False,
        help_text="Chọn gói thời hạn nếu đây là sản phẩm dịch vụ."
    )

    def __init__(self, *args, **kwargs):
        product = kwargs.pop("product", None)
        super().__init__(*args, **kwargs)
        if product is not None:
            self.fields["plan"].queryset = ServicePlan.objects.filter(product=product, is_active=True).order_by("ordering")
            if self.fields["plan"].queryset.exists():
                self.fields["plan"].required = True  # bắt buộc nếu có gói

# shop/forms.py
from django import forms
from decimal import Decimal, InvalidOperation
from .models import Product, Category
import re, unicodedata


# ===================== Helpers =====================

def _slugify_vn(text: str) -> str:
    """
    'Gói dịch vụ 1' -> 'goi-dich-vu-1'
    Bỏ dấu + ký tự đặc biệt, thay bằng '-'
    """
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text)
    return text.strip("-").lower() or "item"


def _unique_slug(model, base_slug: str, instance=None) -> str:
    """
    Tạo slug duy nhất: nếu base_slug đã tồn tại -> thêm -1, -2, ...
    """
    qs = model.objects.all()
    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)

    candidate = base_slug
    i = 1
    while qs.filter(slug=candidate).exists():
        candidate = f"{base_slug}-{i}"
        i += 1
    return candidate


def parse_decimal_vn(s: str) -> Decimal:
    """
    Chuẩn hoá chuỗi số theo thói quen VN:
      - "40.000" -> 40000
      - "1.234,56" -> 1234.56
      - "40,5" -> 40.5
      - "40000.75" -> 40000.75
    """
    s = (s or "").strip().replace(" ", "")
    if not s:
        raise InvalidOperation("empty")

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # dạng 1.234,56 -> bỏ . (ngăn cách nghìn), đổi , -> .
        s = s.replace(".", "").replace(",", ".")
    elif has_comma and not has_dot:
        # dạng 40,5 -> 40.5
        s = s.replace(",", ".")
    elif has_dot and not has_comma:
        # Nếu toàn bộ theo nhóm nghìn: 1.234.567 -> bỏ hết .
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
            s = s.replace(".", "")
        # ngược lại: coi '.' là dấu thập phân (giữ nguyên)

    return Decimal(s)


# ===================== Forms =====================

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug")

    def clean_slug(self):
        name = self.cleaned_data.get("name", "")
        slug_in = self.cleaned_data.get("slug")
        base = _slugify_vn(slug_in or name)
        return _unique_slug(Category, base, self.instance)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("category", "name", "slug", "image", "description", "price", "stock")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"step": "1", "min": "0"}),
        }

    # --- Slug auto +1 nếu trùng ---
    def clean_slug(self):
        name = self.cleaned_data.get("name", "")
        slug_in = self.cleaned_data.get("slug")
        base = _slugify_vn(slug_in or name)
        return _unique_slug(Product, base, self.instance)

    # --- Chuẩn hoá giá ---
    def clean_price(self):
        # Lấy từ self.data để giữ nguyên chuỗi gõ (có dấu . ,)
        raw = self.data.get("price", "")
        try:
            price = parse_decimal_vn(raw)
        except InvalidOperation:
            raise forms.ValidationError("Giá không hợp lệ. Ví dụ: 40000, 40.000, 1.234,56, 40000.75")
        if price < 0:
            raise forms.ValidationError("Giá không được âm.")
        return price

    # --- Chuẩn hoá tồn kho ---
    def clean_stock(self):
        raw = (self.data.get("stock", "") or "").replace(" ", "")
        if raw == "":
            return 0
        # Chấp nhận 1.200 hoặc 1,200 là 1200
        raw = raw.replace(".", "").replace(",", "")
        if not raw.isdigit():
            raise forms.ValidationError("Tồn kho phải là số nguyên không âm.")
        stock = int(raw)
        if stock < 0:
            raise forms.ValidationError("Tồn kho không được âm.")
        return stock

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if Product.objects.exclude(pk=self.instance.pk).filter(name__iexact=name).exists():
            raise forms.ValidationError("Tên sản phẩm đã tồn tại, vui lòng chọn tên khác.")
        return name

# --- Widget hỗ trợ upload nhiều file ---
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultiOptionalFileField(forms.FileField):
    def to_python(self, data):
        # Khi không chọn file, widget multiple trả [] -> coi như None
        if data in (None, "", [], (), False):
            return None
        return data

class ProductImagesForm(forms.Form):
    images = MultiOptionalFileField(
        widget=MultipleFileInput(attrs={"multiple": True, "id": "id_images"}),
        required=False,
        label="Ảnh bổ sung",
        help_text="Giữ Ctrl để chọn nhiều ảnh.",
    )

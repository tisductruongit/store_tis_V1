# news/models.py
from __future__ import annotations

from io import BytesIO
import os

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from PIL import Image, ImageOps


def _unique_slugify(instance: "News", base: str) -> str:
    """
    Tạo slug duy nhất dựa vào `base`.
    """
    slug_base = slugify(base or "") or "item"
    slug = slug_base
    i = 1
    Model = instance.__class__
    while Model.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
        slug = f"{slug_base}-{i}"
        i += 1
    return slug


class News(models.Model):
    # Nội dung chính
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    body = models.TextAreaField if False else models.TextField()  # giữ TextField

    # Ảnh & xuất bản
    image = models.ImageField(upload_to="news/", blank=True, null=True)
    is_published = models.BooleanField(default=True, db_index=True)

    # Liên kết gợi ý (tuỳ chọn)
    link_url = models.URLField(blank=True, default="")
    link_label = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Ví dụ: Đọc tại nguồn / Xem ngay",
    )

    # Toạ độ crop (pixel gốc)
    crop_x = models.IntegerField(default=0, blank=True)
    crop_y = models.IntegerField(default=0, blank=True)
    crop_w = models.IntegerField(default=0, blank=True)
    crop_h = models.IntegerField(default=0, blank=True)

    # Metadata
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "News"
        verbose_name_plural = "News"

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("news:detail", kwargs={"slug": self.slug})

    # ---------- Helpers ----------
    @staticmethod
    def _detect_format_from_name(name: str) -> str:
        ext = os.path.splitext(name or "")[1].lower()
        if ext in (".jpg", ".jpeg"):
            return "JPEG"
        if ext == ".png":
            return "PNG"
        if ext == ".webp":
            return "WEBP"
        # Mặc định PNG để giữ alpha nếu có
        return "PNG"

    def _crop_current_image_if_needed(self) -> None:
        """
        Mở tựa ảnh hiện tại, sửa orientation theo EXIF, crop theo toạ độ pixel gốc,
        rồi lưu đè với hậu tố `_c`.
        """
        if not self.image:
            return
        if not (self.crop_w and self.crop_h):
            return

        # Mở ảnh & sửa xoay theo EXIF (tránh crop lệch trên ảnh mobile)
        self.image.open()
        img = Image.open(self.image)
        img = ImageOps.exif_transpose(img)

        # Tính box crop an toàn trong bounds
        x = max(0, int(self.crop_x))
        y = max(0, int(self.crop_y))
        w = max(0, int(self.crop_w))
        h = max(0, int(self.crop_h))

        left, top = x, y
        right, bottom = min(img.width, x + w), min(img.height, y + h)
        if right <= left or bottom <= top:
            return  # toạ độ không hợp lệ → bỏ qua crop

        cropped = img.crop((left, top, right, bottom))

        # Chọn format theo phần mở rộng gốc
        fmt = self._detect_format_from_name(self.image.name)

        # JPEG không hỗ trợ alpha → chuyển sang RGB
        if fmt == "JPEG" and cropped.mode in ("RGBA", "LA", "P"):
            cropped = cropped.convert("RGB")

        # Ghi bộ nhớ
        buf = BytesIO()
        save_kwargs = {}
        if fmt == "JPEG":
            save_kwargs["quality"] = 90
            save_kwargs["optimize"] = True
        elif fmt == "PNG":
            save_kwargs["optimize"] = True
        cropped.save(buf, fmt, **save_kwargs)

        # Tạo tên mới với hậu tố _c
        root, ext = os.path.splitext(self.image.name or "image")
        new_ext = {
            "JPEG": ".jpg",
            "PNG": ".png",
            "WEBP": ".webp",
        }.get(fmt, ".png")
        new_name = f"{root}_c{new_ext}"

        # Lưu vào ImageField nhưng CHƯA commit DB
        self.image.save(new_name, ContentFile(buf.getvalue()), save=False)

        # Tuỳ chọn: reset crop về 0 để tránh crop lại lần sau
        self.crop_x = self.crop_y = self.crop_w = self.crop_h = 0

    # ---------- Save ----------
    def save(self, *args, **kwargs):
        """
        - Lần đầu `super().save()` để có file path.
        - Nếu có toạ độ crop > 0 → crop & `super().save(update_fields=['image', ...])`.
        - Tự sinh slug duy nhất nếu chưa có.
        """
        # Tạo slug nếu cần
        if not self.slug:
            self.slug = _unique_slugify(self, self.title)

        # Lưu lần 1 để chắc chắn có file
        super().save(*args, **kwargs)

        # Crop nếu có yêu cầu
        if self.image and self.crop_w and self.crop_h:
            try:
                self._crop_current_image_if_needed()
                # Lưu lần 2: chỉ cập nhật image & crop fields
                super().save(
                    update_fields=[
                        "image",
                        "crop_x",
                        "crop_y",
                        "crop_w",
                        "crop_h",
                    ]
                )
            except Exception:
                # Không làm crash yêu cầu chính (ghi log nếu cần)
                pass

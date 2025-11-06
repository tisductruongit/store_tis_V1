# shop/middleware.py
from datetime import date
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import PageView

class PageViewMiddleware(MiddlewareMixin):
    EXCLUDE_PREFIXES = ("/admin/", "/static/", "/media/")

    def process_request(self, request):
        try:
            # bỏ qua admin/static/media
            path = request.path or "/"
            if any(path.startswith(p) for p in self.EXCLUDE_PREFIXES):
                return

            # đảm bảo có session
            if not request.session.session_key:
                request.session.create()
            skey = request.session.session_key

            # chỉ ghi 1 lần / ngày / session
            now = timezone.now()
            start = timezone.make_aware(timezone.datetime.combine(now.date(), timezone.datetime.min.time()))
            exists = PageView.objects.filter(session_key=skey, created_at__gte=start).exists()
            if exists:
                return

            # lấy IP
            ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")

            PageView.objects.create(
                session_key=skey,
                ip=ip or None,
                path=path[:255],
                user=request.user if request.user.is_authenticated else None,
            )
        except Exception:
            # không làm gián đoạn request khi log lỗi
            pass

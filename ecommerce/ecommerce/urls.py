# ecommerce/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('news/', include('news.urls', namespace='news')),
    path('cart/', include('cart.urls', namespace='cart')),
    path('', include('shop.urls', namespace='shop')),
    
    # Allauth (THÊM DÒNG NÀY)
    path('accounts/', include('allauth.urls')),

    path("cart/", include("cart.urls")),
    path("cart/", include(("cart.urls", "cart"), namespace="cart")),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
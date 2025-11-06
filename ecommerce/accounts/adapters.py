# accounts/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email, user_username
from allauth.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class LinkByEmailAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Nếu social account đã gắn user rồi thì thôi
        if sociallogin.is_existing:
            return

        email = user_email(sociallogin.user)
        if not email:
            return  # không có email thì để allauth xử lý tiếp (có thể yêu cầu bổ sung)

        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return  # email chưa tồn tại -> allauth sẽ tạo user mới như bình thường

        # Nếu đã có user với email này -> tự gắn social account vào user đó
        sociallogin.connect(request, existing_user)

        # Chuyển hướng về trang đích sau login
        raise ImmediateHttpResponse(HttpResponseRedirect(settings.LOGIN_REDIRECT_URL))





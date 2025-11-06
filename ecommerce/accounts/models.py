# accounts/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

def user_avatar_path(instance, filename):
    # users/<username>/avatar/<filename>
    return f"users/{instance.user.username}/avatar/{filename}"

def user_photo_path(instance, filename):
    # users/<username>/photos/<filename>
    return f"users/{instance.profile.user.username}/photos/{filename}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)           # KHÔNG chỉnh sửa từ trang hồ sơ
    # accounts/models.py (Profile)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, default='avatars/default.png')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

class ProfileImage(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=user_photo_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.user.username} photo {self.pk}"

# Tự động tạo Profile khi tạo User
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

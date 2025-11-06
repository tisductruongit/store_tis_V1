# news/forms.py
from django import forms
from .models import News

class NewsForm(forms.ModelForm):
    crop_x = forms.IntegerField(required=False, widget=forms.HiddenInput())
    crop_y = forms.IntegerField(required=False, widget=forms.HiddenInput())
    crop_w = forms.IntegerField(required=False, widget=forms.HiddenInput())
    crop_h = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = News
        fields = (
            "title", "body", "image",
            "link_url", "link_label",
            "crop_x", "crop_y", "crop_w", "crop_h",
            "is_published"
        )
        widgets = {
            "body": forms.Textarea(attrs={"rows": 6}),
        }

    def clean(self):
        data = super().clean()
        for k in ("crop_x", "crop_y", "crop_w", "crop_h"):
            try:
                v = int(float(data.get(k) or 0))
            except Exception:
                v = 0
            data[k] = max(0, v)
        return data

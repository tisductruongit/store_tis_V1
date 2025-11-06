# news/views.py
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from .models import News
from .forms import NewsForm

def news_list(request):
    items = News.objects.all()
    return render(request, 'news/list.html', {'items': items})

def news_detail(request, slug):
    item = get_object_or_404(News, slug=slug)
    return render(request, 'news/detail.html', {'item': item})

@user_passes_test(lambda u: u.is_staff)
def admin_news_create(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author = request.user
            obj.save()
            return redirect('news:list')
    else:
        form = NewsForm()
    return render(request, 'news/admin_news_form.html', {'form': form})

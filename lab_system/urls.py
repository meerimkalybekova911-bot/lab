from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.contrib.auth.models import User

def create_super(request):
    if not User.objects.filter(username='Meerim').exists():
        User.objects.create_superuser('Meerim', 'meerimkalybekova911@gmail.com', 'password123')
        return HttpResponse('Superuser түзүлдү!')
    return HttpResponse('Мурунтан бар!')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('setup/', create_super),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Медиа файлдар үчүн
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
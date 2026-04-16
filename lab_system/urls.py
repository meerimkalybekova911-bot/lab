# lab_system/urls.py (башкы urls.py)
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from accounts import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),  # accounts app'тин URL'дери
]

# Медиа файлдар үчүн
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
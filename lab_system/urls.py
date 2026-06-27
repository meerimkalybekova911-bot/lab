from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.contrib.auth.models import User

def create_super(request):
    user, created = User.objects.get_or_create(username='Meerim')
    user.set_password('Pass1234!')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return HttpResponse('Сырсөз жаңыртылды! Pass1234!')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('setup/', create_super),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Медиа файлдар үчүн
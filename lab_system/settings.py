import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv
 
load_dotenv()
 
BASE_DIR = Path(__file__).resolve().parent.parent
 
# ─── КООПСУЗДУК ──────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-758cs@p&4olhz9yc9rxds#jwdj*7%8s9#-%#$yye6&wj^a%jpe'
)
 
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
 
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.onrender.com',
    os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''),
]
ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]
 
# ─── КОЛДОНМОЛОР ─────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'storages',  # django-storages — S3/Supabase үчүн
]
 
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
 
ROOT_URLCONF = 'lab_system.urls'
 
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
 
WSGI_APPLICATION = 'lab_system.wsgi.application'
 
# ─── БАЗА ─────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')
 
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
 
# ─── СЫРСӨЗ ТЕКШЕРҮҮ ────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
 
# ─── ИНТЕРНАЦИОНАЛИЗАЦИЯ ─────────────────────────────────
LANGUAGE_CODE = 'ky'
TIME_ZONE = 'Asia/Bishkek'
USE_I18N = True
USE_TZ = True
 
# ─── STATIC ФАЙЛДАР (CSS, JS) — WhiteNoise аркылуу ───────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'accounts', 'static'),
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
 
# ─── MEDIA ФАЙЛДАР (сүрөт, PDF) — Supabase S3 аркылуу ────
USE_SUPABASE_STORAGE = os.environ.get('USE_SUPABASE_STORAGE', 'False') == 'True'
 
if USE_SUPABASE_STORAGE:
    # Supabase S3-compatible Storage
    AWS_ACCESS_KEY_ID = os.environ.get('SUPABASE_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('SUPABASE_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('SUPABASE_BUCKET_NAME', 'media')
    AWS_S3_ENDPOINT_URL = os.environ.get('SUPABASE_S3_ENDPOINT')
    AWS_S3_REGION_NAME = os.environ.get('SUPABASE_REGION', 'ap-northeast-2')
 
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = 'public-read'  # FIX: файлдар окуу үчүн ачык болсун
    AWS_QUERYSTRING_AUTH = False  # Шилтеме токенсиз, түз ачылат
    AWS_S3_ADDRESSING_STYLE = 'path'  # Supabase path-style талап кылат
    AWS_S3_SIGNATURE_VERSION = 's3v4'
 
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
 
    # Сүрөт/файл URL'дары Supabase'ден түз көрсөтүлөт
    MEDIA_URL = (
        f"{os.environ.get('SUPABASE_PUBLIC_URL')}/storage/v1/object/public/"
        f"{AWS_STORAGE_BUCKET_NAME}/"
    )
else:
    # Локалда же Supabase орнотулмайын — жөнөкөй локалдык media
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
 
# ─── БАШКА ───────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
 
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
 
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
 
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
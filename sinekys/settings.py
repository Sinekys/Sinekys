# settings.py — versión lista para producción (pegada sobre tu base actual)
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env (asegúrate de no commitear este archivo)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------
# Seguridad básica y entornos
# ---------------------------
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("Falta SECRET_KEY en variables de entorno")

# Controla DEBUG por variable de entorno (por defecto False en prod)
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

# Hosts permitidos — configurar en entorno
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'sinekys.com,www.sinekys.com').split(',')

# Si estás detrás de proxy (ej: nginx, load balancer) activa esta cabecera:
# En nginx: proxy_set_header X-Forwarded-Proto $scheme;
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies seguras solo si usas HTTPS (requerido en prod)
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() in ('1', 'true', 'yes')
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True').lower() in ('1', 'true', 'yes')

# Confía en orígenes para CSRF (usar esquema + dominio). Ej: https://sinekys.com
csf_trusted = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if csf_trusted:
    CSRF_TRUSTED_ORIGINS = [u.strip() for u in csf_trusted.split(',')]
else:
    CSRF_TRUSTED_ORIGINS = []

# Seguridad HTTP
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('1', 'true', 'yes')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True').lower() in ('1', 'true', 'yes')
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True').lower() in ('1', 'true', 'yes')
SECURE_REFERRER_POLICY = os.getenv('SECURE_REFERRER_POLICY', 'no-referrer-when-downgrade')
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------------------------
# Emails (SMTP / proveedor)
# ---------------------------
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'no-reply@sinekys.com')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = os.getenv('EMAIL_SUBJECT_PREFIX', '[Sinekys] ')

# ---------------------------
# Aplicaciones y middleware
# ---------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'django.contrib.sites',

    # Sinekys apps
    'accounts',
    'core',
    'ejercicios',
    'subscriptions',
    'usage',

    # Third-party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'widget_tweaks',
    'tailwind',
    'theme',
    'mathfilters',

    # dev-only (si DEBUG); no deben estar en prod
    *(['django_browser_reload'] if DEBUG else []),
]

SITE_ID = int(os.getenv('DJANGO_SITE_ID', '1'))

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # Whitenoise (sirve archivos estáticos desde app si no usas S3)
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'sinekys.urls'

# ---------------------------
# Templates
# ---------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sinekys.wsgi.application'

# ---------------------------
# Database (postgres)
# ---------------------------
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': os.getenv('DB_OPTIONS', ''),
    }
}

# ---------------------------
# Caché (opcional Redis)
# ---------------------------
if os.getenv('REDIS_URL'):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv('REDIS_URL'),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# ---------------------------
# Password validation
# ---------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# ---------------------------
# Internacionalización y zona horaria
# ---------------------------
LANGUAGE_CODE = 'es-es'
TIME_ZONE = os.getenv('TIME_ZONE', 'UTC')
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ---------------------------
# Archivos estáticos y media
# ---------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # collectstatic target
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
# WhiteNoise: compresión y cache para static files (si no usas S3)
STATICFILES_STORAGE = os.getenv('STATICFILES_STORAGE', 'whitenoise.storage.CompressedManifestStaticFilesStorage')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Opcional S3 (activar con env USE_S3=1 y vars S3_*)
USE_S3 = os.getenv('USE_S3', 'False').lower() in ('1', 'true', 'yes')
if USE_S3:
    # requiere django-storages[boto3]
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN', f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com")
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"

# ---------------------------
# Auth & Allauth
# ---------------------------
AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_ADAPTER = os.getenv('ACCOUNT_ADAPTER', 'accounts.adapter.CustomAccountAdapter')
ACCOUNT_SIGNUP_FORM_CLASS = os.getenv('ACCOUNT_SIGNUP_FORM_CLASS', 'accounts.forms.CustomSignupForm')
ACCOUNT_EMAIL_VERIFICATION = os.getenv('ACCOUNT_EMAIL_VERIFICATION', 'mandatory')
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = int(os.getenv('ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS', '1'))
ACCOUNT_DEFAULT_HTTP_PROTOCOL = os.getenv('ACCOUNT_DEFAULT_HTTP_PROTOCOL', 'https')
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = os.getenv('ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION', 'True').lower() in ('1', 'true', 'yes')
ACCOUNT_MAX_EMAIL_ADDRESSES = int(os.getenv('ACCOUNT_MAX_EMAIL_ADDRESSES', '3'))

LOGIN_REDIRECT_URL = os.getenv('LOGIN_REDIRECT_URL', '/')

# ---------------------------
# Límites y flags propios
# ---------------------------
DIAGNOSTICO_MAX_EJERCICIOS = int(os.getenv('DIAGNOSTICO_MAX_EJERCICIOS', '30'))
DIAGNOSTICO_UMBRAL_SE = float(os.getenv('DIAGNOSTICO_UMBRAL_SE', '0.4'))
DIAGNOSTICO_UMBRAL_EXTREMO = float(os.getenv('DIAGNOSTICO_UMBRAL_EXTREMO', '2.9'))

# ---------------------------
# Celery (opcional)
# ---------------------------
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')  # ej: redis://:pass@host:6379/0
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)

# ---------------------------
# Logging (console + file; Sentry si está configurado)
# ---------------------------
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs", "sinekys.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "standard",
        },
    },
    "root": {"handlers": ["console", "file"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
        "sinekys": {"handlers": ["console", "file"], "level": LOG_LEVEL, "propagate": False},
    }
}

# Crear carpeta logs si no existe
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

# Sentry (opcional)
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()], traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.0')))
    except Exception:
        pass

# ---------------------------
# Misc
# ---------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Seguridad adicional para cookies de sesión
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # generalmente False para compatibilidad con JS si usas fetch + csrf cookie

# Si quieres controlar CORS más fino en prod, cambia CORS_ORIGIN_ALLOW_ALL a False y define la whitelist:
CORS_ORIGIN_ALLOW_ALL = os.getenv('CORS_ORIGIN_ALLOW_ALL', 'False').lower() in ('1', 'true', 'yes')
if not CORS_ORIGIN_ALLOW_ALL:
    cors_whitelist = os.getenv('CORS_ORIGIN_WHITELIST', '')
    CORS_ALLOWED_ORIGINS = [u.strip() for u in cors_whitelist.split(',')] if cors_whitelist else []

# FIN del settings

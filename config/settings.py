"""
Django settings for config project.
"""

from pathlib import Path

from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'research.apps.ResearchConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
}

# Celery
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_TASK_TIME_LIMIT = 60 * 20
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 18
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# Email
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
MANAGER_EMAIL = config('MANAGER_EMAIL')


# Gemini - Multi Key Rotation (5 keys, different accounts)
GEMINI_API_KEYS = [
    config('GEMINI_API_KEY_1'),
    config('GEMINI_API_KEY_2'),
    config('GEMINI_API_KEY_3'),
    config('GEMINI_API_KEY_4'),
    config('GEMINI_API_KEY_5'),
]
GEMINI_MODEL_ID = config('GEMINI_MODEL_ID', default='gemini-3.5-flash-lite')
GEMINI_BACKUP_MODEL_ID = config('GEMINI_BACKUP_MODEL_ID', default='gemini-3.5-flash')

# Groq - Multi Key Rotation (5 keys, different accounts)
GROQ_API_KEYS = [
    config('GROQ_API_KEY_1', default=''),
    config('GROQ_API_KEY_2', default=''),
    config('GROQ_API_KEY_3', default=''),
    config('GROQ_API_KEY_4', default=''),
    config('GROQ_API_KEY_5', default=''),
]

LLM_EXTRACTION_ORDER = ['groq', 'gemini']
LLM_DISCOVERY_ORDER = ['gemini', 'groq']

# Crawl4AI
CRAWL4AI_ENABLED = config('CRAWL4AI_ENABLED', default=True, cast=bool)
CRAWL4AI_TIMEOUT_MS = config('CRAWL4AI_TIMEOUT_MS', default=25000, cast=int)





# Scraper
SCRAPER_REQUEST_TIMEOUT = config('SCRAPER_REQUEST_TIMEOUT', default=10, cast=int)
SCRAPER_MAX_PAGES_PER_COMPANY = config('SCRAPER_MAX_PAGES_PER_COMPANY', default=4, cast=int)
SCRAPER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'standard'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    # Crawl4AI ke internal logs WARNING tak dabao:
    'loggers': {
        'crawl4ai': {'level': 'ERROR'},
    },
}



# Cache (Redis - shared across workers)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/0'),
    }
}


# Global dedup: skip companies that already exist in DB with usable data
SKIP_EXISTING_COMPANIES = config('SKIP_EXISTING_COMPANIES', default=True, cast=bool)
TAVILY_API_KEY = config('TAVILY_API_KEY', default='')

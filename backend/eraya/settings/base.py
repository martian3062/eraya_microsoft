from pathlib import Path
import environ

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(BASE_DIR.parent / '.env')

SECRET_KEY = env('SECRET_KEY', default='dev-secret-key-please-change')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'channels',
]

LOCAL_APPS = [
    'apps.agents',
    'apps.domains',
    'apps.decisions',
    'apps.incidents',
    'apps.audit',
    'apps.eraya_auth',
    'apps.frontend',
    'apps.trading',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eraya.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'eraya.wsgi.application'
ASGI_APPLICATION = 'eraya.asgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
}

REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])
CORS_ALLOW_CREDENTIALS = True

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Eraya framework config ────────────────────────────────────────────────────
ERAYA = {
    'GROQ_API_KEY': env('GROQ_API_KEY', default=''),
    'HUGGINGFACE_TOKEN': env('HUGGINGFACE_TOKEN', default=''),
    'NATS_URL': env('NATS_URL', default='nats://localhost:4222'),
    'CHROMA_HOST': env('CHROMA_HOST', default='localhost'),
    'CHROMA_PORT': env.int('CHROMA_PORT', default=8001),
    'A2A_BUS_BACKEND': env('A2A_BUS_BACKEND', default='redis'),
    'ML_DEVICE': env('ML_DEVICE', default='cpu'),
    'ENABLE_GUARDIAN': env.bool('ENABLE_GUARDIAN', default=True),
    'LATENCY_BUDGET_MS': env.int('LATENCY_BUDGET_MS', default=500),

    # Agentic AI providers (caspr upgrade) - all optional, graceful fallback
    # LLM cascade (Tier 1): Groq -> Kimi -> local open-source HF model
    'KIMI_API_KEY': env('KIMI_API_KEY', default=''),
    'SARVAM_API_KEY': env('SARVAM_API_KEY', default=''),
    'GROQ_MODEL': env('GROQ_MODEL', default='llama-3.3-70b-versatile'),
    'KIMI_MODEL': env('KIMI_MODEL', default='kimi-k2-0711-preview'),
    'HF_LOCAL_LLM_ENABLED': env('HF_LOCAL_LLM_ENABLED', default='false'),
    'HF_LOCAL_LLM_MODEL': env('HF_LOCAL_LLM_MODEL', default='flan-t5-small'),
    # ML (Tier 2)
    'HF_TOKEN': env('HF_TOKEN', default=env('HUGGINGFACE_TOKEN', default='')),
    'TABPFN_API_KEY': env('TABPFN_API_KEY', default=''),
    # Memory
    'PINECONE_API_KEY': env('PINECONE_API_KEY', default=''),
    'PINECONE_INDEX': env('PINECONE_INDEX', default='eraya'),
    'PINECONE_DIMENSION': env.int('PINECONE_DIMENSION', default=384),
    'PINECONE_CLOUD': env('PINECONE_CLOUD', default='aws'),
    'PINECONE_REGION': env('PINECONE_REGION', default='us-east-1'),
    'CYBORGDB_API_KEY': env('CYBORGDB_API_KEY', default=''),
    # Ingestion
    'FIRECRAWL_API_KEY': env('FIRECRAWL_API_KEY', default=''),
    'BRIGHTDATA_API_KEY': env('BRIGHTDATA_API_KEY', default=''),
    'ZENROWS_API_KEY': env('ZENROWS_API_KEY', default=''),
    'TINYFISH_API_KEY': env('TINYFISH_API_KEY', default=''),
    # Orchestration / dev / assets
    'N8N_WEBHOOK_URL': env('N8N_WEBHOOK_URL', default=''),
    'N8N_API_KEY': env('N8N_API_KEY', default=''),
    'ZERVE_API_KEY': env('ZERVE_API_KEY', default=''),
    'STITCH_API_KEY': env('STITCH_API_KEY', default=''),
    'PEXELS_API_KEY': env('PEXELS_API_KEY', default=''),
}

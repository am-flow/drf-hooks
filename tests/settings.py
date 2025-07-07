import os

HOOK_EVENTS_OVERRIDE = {
    "comment.added": "django_comments.Comment.created",
    "comment.changed": "django_comments.Comment.updated",
    "comment.removed": "django_comments.Comment.deleted",
    "comment.moderated": "django_comments.Comment.moderated",
    "special.thing": None,
}

HOOK_SERIALIZERS_OVERRIDE = {
    "django_comments.Comment": "tests.test_hooks.CommentSerializer",
}

ALT_HOOK_EVENTS = dict(HOOK_EVENTS_OVERRIDE)
ALT_HOOK_EVENTS["comment.moderated"] += "+"
ALT_HOOK_SERIALIZERS = {}


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "test-secret-key-for-testing"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "django.contrib.sites",
    "django_comments",
    "drf_hooks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "test_urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEMPLATES = (
    [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        },
    ],
)
SITE_ID = 1
HOOK_EVENTS = HOOK_EVENTS_OVERRIDE
HOOK_THREADING = False
HOOK_SERIALIZERS = HOOK_SERIALIZERS_OVERRIDE
# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

import json
import logging
import os

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_DIR = os.path.join(BASE_DIR, "secrets")


def get_secret(filename):
    with open(os.path.join(SECRETS_DIR, filename)) as f:
        return f.read().strip()


SECRET_KEY = get_secret("secret_key.txt")

DEBUG = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

ALLOWED_HOSTS = ["www.opsgrid.net"]
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "opsgrid.core",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "bootstrapform",
    "rest_framework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "opsgrid.core.middleware.CacheDefaultOffMiddleware",
]

ROOT_URLCONF = "opsgrid.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "opsgrid.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/opt/opsgrid-web/opsgrid-web_db.sqlite3",
    }
}


AUTH_USER_MODEL = "core.User"
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = "/assets/"
STATIC_ROOT = "/opt/opsgrid-web/assets"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "pack-dist")]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"level": "INFO", "handlers": ["console_verbose"]},
    "formatters": {
        "simple": {"format": "%(levelname)s: %(asctime)s - %(name)s: %(message)s"},
        "withfile": {
            "format": "%(levelname)s: %(asctime)s - %(name)s (%(module)s:%(lineno)s): %(message)s"
        },
    },
    "handlers": {
        "console_simple": {"class": "logging.StreamHandler", "formatter": "simple"},
        "console_verbose": {"class": "logging.StreamHandler", "formatter": "withfile"},
    },
    "loggers": {
        "django": {
            "handlers": ["console_simple"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console_simple"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "opsgrid": {
            "handlers": ["console_verbose"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

INGEST_CLIENT_SECRET = get_secret("ingest_client_secret.txt")

EMAIL_BACKEND = "django_amazon_ses.EmailBackend"
AWS_ACCESS_KEY_ID = get_secret("ses.id")
AWS_SECRET_ACCESS_KEY = get_secret("ses.key")
DEFAULT_FROM_EMAIL = "Opsgrid <noreply@opsgrid.net>"
ADMINS = (("Simon", "simon@simonmweber.com"),)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

SITE_ID = 1
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_FORMS = {
    "signup": "opsgrid.core.forms.SignupFormUsernameFocus",
}
LOGIN_REDIRECT_URL = "/dashboard"

SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email", "https://www.googleapis.com/auth/drive.file"],
        "AUTH_PARAMS": {"access_type": "offline", "prompt": "consent"},
    }
}
_google_creds = json.loads(get_secret("opsgrid-web.client-auth.json"))
GOOGLE_OAUTH_CLIENT_ID = _google_creds["web"]["client_id"]
GOOGLE_OAUTH_SECRET = _google_creds["web"]["client_secret"]

sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.WARNING)
sentry_sdk.init(
    dsn=get_secret("sentry.dsn"),
    integrations=[DjangoIntegration(), sentry_logging],
    send_default_pii=True,
)

SEND_GA_EVENTS = True
GA_TRACKING_ID = "UA-169365761-1"

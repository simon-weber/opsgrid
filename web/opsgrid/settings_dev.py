from .settings import *  # noqa

SECRET_KEY = "dev_secret_key"
DEBUG = True
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
X_FRAME_OPTIONS = "SAMEORIGIN"
USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = None

ALLOWED_HOSTS.append("*")  # noqa: F405

AUTH_PASSWORD_VALIDATORS = []

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "opsgrid-web_db.sqlite3"),  # noqa: F405
    }
}

# disable sentry
sentry_sdk.init(dsn="")  # noqa: F405

SEND_GA_EVENTS = False

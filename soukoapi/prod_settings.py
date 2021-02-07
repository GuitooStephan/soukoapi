from .base_settings import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DEBUG = False

SECURE_SSL_REDIRECT = True

ALLOWED_HOSTS = ["*"]

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[DjangoIntegration()],
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)

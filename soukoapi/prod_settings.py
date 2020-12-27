from .base_settings import *

DEBUG = False

SECURE_SSL_REDIRECT = True

ALLOWED_HOSTS = ["*"]

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

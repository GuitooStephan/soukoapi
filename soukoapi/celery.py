from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from kombu import Queue, Exchange
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "soukoapi.dev_settings")

app = Celery("soukoapi", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
    CELERY_IGNORE_RESULT=True,
    CELERY_ACKS_LATE=True,  # Allows executing task to be send to the next worker if current worker crushes.
    CELERY_QUEUES=(
        Queue("send_email", routing_key="send_email"),
        Queue("fetch_reports", routing_key="fetch_reports"),
    ),
    CELERY_ROUTES={
        "main.tasks.send_email_async": {"queue": "send_email"},
        "main.tasks.create_store_orders_metrics": {"queue": "fetch_reports"},
        "main.tasks.create_store_profit_metrics": {"queue": "fetch_reports"}
    },
)
app.conf.broker_transport_options = {"queue_order_strategy": "priority"}
app.conf.task_default_queue = "celery"
app.conf.timezone = "UTC"

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

if __name__ == "__main__":
    app.start()

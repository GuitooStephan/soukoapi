from dateutil.relativedelta import relativedelta
from django.utils import timezone as dj_timezone
from soukoapi.celery import app
from celery import shared_task, Task

from django.core.exceptions import ObjectDoesNotExist

from .utils.mail.emailer import (
    Emailer
)
from . import models

@shared_task(
    bind=True,
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_email_async(
    self,
    template_id,
    tos,
    subject,
    context,
    index
):
    Emailer( template_id, tos, subject, context, index ).send()


@shared_task(bind=True)
def create_store_orders_metrics(self, store_id):
    try:
        store = models.Store.objects.get(pk=store_id)
        timestamped_metric, _ = models.OrdersTimestampedMetric.objects.get_or_create(
            date=dj_timezone.now().date(), store=store, orders=store.orders.count()
        )
    except ObjectDoesNotExist:
        pass
    except Exception as e:
        print( str(e) )



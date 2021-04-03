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
        today = dj_timezone.now().date()
        timestamped_metric, _ = models.OrdersTimestampedMetric.objects.get_or_create(
            date=today, store=store
        )
        timestamped_metric.orders = store.orders.filter(created_at__year=today.year, created_at__month=today.month, created_at__day=today.day, confirmed=True).count()
        timestamped_metric.save()
    except ObjectDoesNotExist:
        pass
    except Exception as e:
        print( str(e) )


@shared_task(bind=True)
def create_store_profit_metrics(self, store_id):
    try:
        store = models.Store.objects.get(pk=store_id)
        today = dj_timezone.now().date()
        timestamped_metric, _ = models.ProfitTimestampedMetric.objects.get_or_create(
            date=today, store=store
        )
        orders = store.orders.filter(paid_on__year=today.year, paid_on__month=today.month, paid_on__day=today.day, confirmed=True)
        timestamped_metric.profit = float( sum(o.profit for o in orders) )
        timestamped_metric.save()
    except ObjectDoesNotExist:
        pass
    except Exception as e:
        print( str(e) )



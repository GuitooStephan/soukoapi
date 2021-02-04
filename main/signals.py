from urllib.parse import urljoin

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.urls import reverse
from django.conf import settings
from django_rest_passwordreset.signals import reset_password_token_created

from main.tasks import (
    send_email_async,
)
from .models import (
    Store,
    StorePeriodicTask
)

@receiver(reset_password_token_created)
def password_reset_token_created(
    sender, instance, reset_password_token, *args, **kwargs
):
    user = reset_password_token.user
    reset_password_url = f"/account/auth/forgot-password/reset-password?token={reset_password_token.key}&email={reset_password_token.user.email}"
    emailer = send_email_async.delay(
        template_id=settings.TEMPLATE_EMAIL_WITH_URL_ID,
        tos=[reset_password_token.user.email],
        subject='Souko - Reset Password',
        context={
            'subject': 'Souko - Reset Password',
            'first_name': reset_password_token.user.first_name,
            'message': '''You are about to reset your password. Kindly click on the link below to complete the process''',
            'url': '{}'.format(urljoin( settings.FRONTEND_BASE_URL, reset_password_url ))
        },
        index=0
    )


@receiver(post_save, sender=Store)
def store_created( sender, instance, created, **kwargs ):
    if created:
        StorePeriodicTask.objects.schedule_create_store_orders_metrics( instance )
        StorePeriodicTask.objects.schedule_create_store_profit_metrics( instance )

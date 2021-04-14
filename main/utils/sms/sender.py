import logging

from django.conf import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)

def send( body, to ):
    client = Client( getattr( settings, 'TWILIO_ACCOUNT_SID' ), getattr( settings, 'TWILIO_AUTH_TOKEN' ) )
    client.messages.create(
        body=body,
        from_=getattr( settings, 'TWILIO_NUMBER' ),
        to=to
    )
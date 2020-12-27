import logging
import time
import sendgrid
from sendgrid.helpers.mail import (
    Mail, Content, To, Subject, Substitution,
    MimeType, TemplateId, From, DynamicTemplateData
)
from python_http_client import exceptions

from django.conf import settings

logger = logging.getLogger(__name__)

sg = sendgrid.SendGridAPIClient(getattr(settings, 'SENDGRID_API_KEY'))

class Emailer(object):
    def __init__(self, template_id, tos, subject, context, index):
        self.message = Mail()
        self._compose( template_id, subject )
        self.add_personalization( tos, subject, context, index )

    def _compose(self, template_id, subject):
        self.message.content = Content(MimeType.html, '<strong>Souko</strong>')
        self.message.template_id = TemplateId(template_id)
        self.message.subject = subject
        self.message.from_email = From(getattr(settings, 'SENDER_EMAIL'), 'Souko')

    def add_personalization(self, tos, subject, template_data, index):
        self.message.to = [To(to, '', p=index) for to in tos]
        self.message.subject = Subject(subject, p=index)
        self.message.dynamic_template_data = DynamicTemplateData(template_data, p=index)

    def send(self):
        try:
            response = sg.send(message=self.message.get())
            return response.status_code
        except (exceptions.InternalServerError, exceptions.ServiceUnavailableError,
                exceptions.TooManyRequestsError) as e:
            time.sleep(60)
            self.send()
        except exceptions.BadRequestsError as e:
            logger.exception('[EXCEPTION] Bad request')
            raise(Exception(e.reason))
        except Exception as e:
            raise(e)

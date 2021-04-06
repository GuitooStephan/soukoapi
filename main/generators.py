from datetime import datetime

from django.utils.crypto import get_random_string


def generate_verification_code():
    return get_random_string(length=6, allowed_chars="1234567890")


def generate_order_number():
    now = datetime.now()
    return f"{get_random_string(length=4, allowed_chars='ABCDEFJHIGKLMNOPQRSTUVWXYZ')}{now.strftime('%m%d%Y%H%M%S')}"

from .models import Notification

import secrets
import string




def create_notification(recipient, title, message, sender=None, link=None, category="system"):

    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        link=link,
        category=category
    )




def generate_temp_password():
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(8))
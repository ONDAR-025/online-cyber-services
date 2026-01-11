"""
ASGI config for lms_config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# This will ensure Celery app is imported when Django starts
from .celery import app as celery_app

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_config.settings')

application = get_asgi_application()

__all__ = ('celery_app', 'application')

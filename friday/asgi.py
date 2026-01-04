"""
ASGI config for friday project.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'friday.settings')

application = get_asgi_application()

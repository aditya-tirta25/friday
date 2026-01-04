"""
Configuration settings imported from local_settings.

This file imports sensitive configuration from local_settings/cfg.py
which should not be committed to version control.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(BASE_DIR))

try:
    from local_settings.cfg import DATABASE, MATRIX_HOMESERVER, MATRIX_USERNAME, MATRIX_PASSWORD, OPENAI_API_KEY, OPENAI_BASE_URL
except ImportError:
    raise ImportError(
        "Could not import local_settings/cfg.py. "
        "Please create this file with your database and API credentials. "
        "See local_settings/cfg.py.example for reference."
    )

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DATABASE.get('NAME', 'friday'),
        'USER': DATABASE.get('USER', 'postgres'),
        'PASSWORD': DATABASE.get('PASSWORD', ''),
        'HOST': DATABASE.get('HOST', 'localhost'),
        'PORT': DATABASE.get('PORT', '5432'),
    }
}

MATRIX_CONFIG = {
    'HOMESERVER': MATRIX_HOMESERVER,
    'USERNAME': MATRIX_USERNAME,
    'PASSWORD': MATRIX_PASSWORD,
}

OPENAI_CONFIG = {
    'API_KEY': OPENAI_API_KEY,
    'BASE_URL': OPENAI_BASE_URL,
}

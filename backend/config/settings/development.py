from .base import *  # noqa: F403

DEBUG = True

# Django's threaded development server creates short-lived request threads.
DATABASES['default']['CONN_MAX_AGE'] = 0  # noqa: F405

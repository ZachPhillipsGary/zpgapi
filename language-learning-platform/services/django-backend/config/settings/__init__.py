"""Settings module."""
from .base import *

# Import environment-specific settings
import os
env = os.environ.get('DJANGO_ENV', 'development')

if env == 'production':
    from .production import *
elif env == 'development':
    from .development import *

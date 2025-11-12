"""Learning Plans app configuration"""
from django.apps import AppConfig


class LearningPlansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.learning_plans'
    verbose_name = 'Learning Plans'

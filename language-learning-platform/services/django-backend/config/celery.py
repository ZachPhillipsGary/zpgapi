"""Celery configuration"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('mala_language_learning')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Generate daily personalized podcasts at 6 AM
    'generate-daily-podcasts': {
        'task': 'apps.languages.tasks.generate_daily_podcasts_for_all_users',
        'schedule': crontab(hour=6, minute=0),
    },
    # Generate daily content at 2 AM
    'generate-daily-stories': {
        'task': 'apps.languages.tasks.generate_daily_stories',
        'schedule': crontab(hour=2, minute=0),
    },
    'generate-daily-quizzes': {
        'task': 'apps.languages.tasks.generate_daily_quizzes',
        'schedule': crontab(hour=2, minute=30),
    },
    'generate-daily-flashcards': {
        'task': 'apps.languages.tasks.generate_daily_flashcards',
        'schedule': crontab(hour=3, minute=0),
    },
    # Process pending AI jobs every 10 minutes
    'process-ai-jobs': {
        'task': 'apps.languages.tasks.process_pending_ai_jobs',
        'schedule': crontab(minute='*/10'),
    },
    # Clean up old sessions
    'cleanup-old-sessions': {
        'task': 'apps.languages.tasks.cleanup_old_tutoring_sessions',
        'schedule': crontab(hour=1, minute=0),
    },
}

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

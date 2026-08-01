# config/celery.py
import os
from celery import Celery

# 🔴 Remplacer 'ecabinet.settings' par 'config.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
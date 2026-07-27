import os
from celery import Celery

# Définir le module de réglages par défaut de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecabinet.settings')

app = Celery('ecabinet')

# Charger les configurations depuis settings.py avec le préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Détecter automatiquement les fichiers tasks.py dans chaque application Django
app.autodiscover_tasks()
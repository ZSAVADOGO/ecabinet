# apps/core/apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'   # cohérent avec le sys.path.insert(BASE_DIR / 'apps') déjà en place dans ton settings.py
from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    #name = 'authentication'
    name = 'apps.authentication'
    label = 'authentication'  # <-- Crucial pour correspondre à 'authentication.User'

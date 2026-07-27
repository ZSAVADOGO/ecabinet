# authentication/backends.py
from django.contrib.auth.backends import ModelBackend
from django.utils import timezone
from apps.authentication.models import User


class CabinetAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            # Hash factice pour égaliser le temps de réponse (mitige l'énumération d'emails par timing attack)
            User().set_password(password)
            return None

        if user.est_verrouille():
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            ip = request.META.get('REMOTE_ADDR') if request else None
            user.reinitialiser_tentatives(ip=ip)
            return user

        user.enregistrer_echec_connexion()
        return None
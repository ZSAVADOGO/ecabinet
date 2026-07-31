# apps/core/decorators.py
#Contrôle d'accès par rôle (RBAC), réutilisable partout
from functools import wraps
from django.core.exceptions import PermissionDenied
from apps.core.permissions import peut


""" def role_requis(*roles_autorises):
    def decorateur(vue):
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.role not in roles_autorises:
                raise PermissionDenied("Accès réservé à : " + ", ".join(roles_autorises))
            return vue(request, *args, **kwargs)
        return enveloppe
    return decorateur """


def capacite_requise(nom_capacite):
    def decorateur(vue):
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            if not peut(request.user, nom_capacite):
                raise PermissionDenied(f"Action réservée. Capacité requise : {nom_capacite}")
            return vue(request, *args, **kwargs)
        return enveloppe
    return decorateur
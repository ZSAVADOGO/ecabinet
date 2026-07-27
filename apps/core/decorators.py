# apps/core/decorators.py
#Contrôle d'accès par rôle (RBAC), réutilisable partout
from functools import wraps
from django.core.exceptions import PermissionDenied

def role_requis(*roles_autorises):
    def decorateur(vue):
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.role not in roles_autorises:
                raise PermissionDenied("Accès réservé à : " + ", ".join(roles_autorises))
            return vue(request, *args, **kwargs)
        return enveloppe
    return decorateur
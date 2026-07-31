# apps/core/views.py
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.core.decorators import capacite_requise
from apps.core.services import definir_permission_role, reinitialiser_permission_role


@capacite_requise('gerer_utilisateurs')
@require_http_methods(["POST"])
def api_definir_permission_role(request):
    payload = json.loads(request.body)
    role = payload.get("role")
    capacite = payload.get("capacite")
    autorise = payload.get("autorise")

    try:
        if autorise is None:
            reinitialiser_permission_role(role, capacite)
            message = "Revenu à la valeur par défaut."
        else:
            definir_permission_role(role, capacite, bool(autorise), request.user)
            message = "Permission mise à jour avec succès."
    except Exception as exc:
        return JsonResponse({"erreur": str(exc)}, status=400)

    return JsonResponse({"message": message}, status=200)
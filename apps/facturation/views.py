# facturation/views.py
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from facturation.services import (
    facture_vers_dict,
    lister_factures,
    obtenir_facture,
    creer_facture,
    modifier_facture,
    supprimer_facture,
    options_clients,
    options_dossiers
)

#from facturation.services import facturation_service


#@login_required
def facturation_dashboard(request):
    contexte = {
        "statuts_facture": [
            ("brouillon", "Brouillon"), ("envoyee", "Envoyée"),
            ("payee", "Payée"), ("en_retard", "En retard"),
        ],
        "clients": options_clients(),
        "dossiers": options_dossiers(),
    }
    return render(request, "facturation/facturation_dashboard.html", contexte)


#@login_required
@require_GET
def api_lister_factures(request):
    resultat = lister_factures(
        recherche=request.GET.get("q", "").strip(),
        statut=request.GET.get("statut", ""),
        client_id=request.GET.get("client_id", ""),
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
    )
    return JsonResponse(resultat, status=200)


#@login_required
@require_GET
def api_detail_facture(request, facture_id):
    try:
        facture = obtenir_facture(facture_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Facture introuvable."}, status=404)
    return JsonResponse(facture_vers_dict(facture), status=200)


#@login_required
@require_http_methods(["POST"])
def api_creer_facture(request):
    try:
        payload = json.loads(request.body)
        facture = creer_facture(payload, request.user)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Facture créée avec succès.", "facture": facture_vers_dict(facture)},
        status=201,
    )


#@login_required
@require_http_methods(["POST"])
def api_modifier_facture(request, facture_id):
    try:
        payload = json.loads(request.body)
        facture = modifier_facture(facture_id, payload, request.user)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Facture introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Facture modifiée avec succès.", "facture": facture_vers_dict(facture)},
        status=200,
    )


#@login_required
@require_http_methods(["POST"])
def api_supprimer_facture(request, facture_id):
    try:
        supprimer_facture(facture_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Facture introuvable."}, status=404)

    return JsonResponse({"message": "Facture supprimée avec succès."}, status=200)


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
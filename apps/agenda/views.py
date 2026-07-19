# agenda/views.py
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from agenda.services import (evenement_vers_dict,_queryset_filtre, lister_evenements,obtenir_evenement,
creer_evenement,modifier_evenement,supprimer_evenement,options_dossiers)


#@login_required
def agenda_dashboard(request):
    contexte = {
        "types_evenement": [
            ("audience", "Audience"),
            ("rdv_client", "RDV client"),
            ("delai_procedure", "Délai de procédure"),
            ("autre", "Autre"),
        ],
        "dossiers": options_dossiers(),
    }
    return render(request, "agenda/agenda_dashboard.html", contexte)


#@login_required
@require_GET
def api_lister_evenements(request):
    resultat = lister_evenements(
        recherche=request.GET.get("q", "").strip(),
        type_evenement=request.GET.get("type", ""),
        dossier_id=request.GET.get("dossier_id", ""),
        critique=request.GET.get("critique", ""),
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
    )
    return JsonResponse(resultat, status=200)


#@login_required
@require_GET
def api_detail_evenement(request, evenement_id):
    try:
        evt = obtenir_evenement(evenement_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Événement introuvable."}, status=404)
    return JsonResponse(evenement_vers_dict(evt), status=200)


#@login_required
@require_http_methods(["POST"])
def api_creer_evenement(request):
    try:
        payload = json.loads(request.body)
        evt = creer_evenement(payload, request.user)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Événement créé avec succès.", "evenement": evenement_vers_dict(evt)},
        status=201,
    )


#@login_required
@require_http_methods(["POST"])
def api_modifier_evenement(request, evenement_id):
    try:
        payload = json.loads(request.body)
        evt = modifier_evenement(evenement_id, payload, request.user)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Événement introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Événement modifié avec succès.", "evenement": evenement_vers_dict(evt)},
        status=200,
    )


#@login_required
@require_http_methods(["POST"])
def api_supprimer_evenement(request, evenement_id):
    try:
        supprimer_evenement(evenement_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Événement introuvable."}, status=404)

    return JsonResponse({"message": "Événement supprimé avec succès."}, status=200)


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
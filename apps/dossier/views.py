# dossier/views.py
"""
Contrôleur (vues) du module Dossier.
"""

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from dossier.models import Dossier
#from dossier.services import nom_affichage
#from dossier.services import nom_affichage
from dossier.services import (dossier_vers_dict, lister_dossiers, obtenir_dossier, creer_dossier, modifier_dossier, supprimer_dossier, options_clients, options_avocats)





##@login_required
def dossier_dashboard(request):
    """Rend le template unique du dashboard Dossier (tableau + modals intégrés)."""
    contexte = {
        "statuts_dossier": Dossier.StatutDossier.choices,
        "types_affaire": Dossier.TypeAffaire.choices,
        "clients": options_clients(),
        "avocats": options_avocats(),
    }
    return render(request, "dossier/dossier_dashboard.html", contexte)


##@login_required
@require_GET
def api_lister_dossiers(request):
    """
    Query params : q, statut, type_affaire, client_id, date_debut, date_fin, page, page_size
    """
    resultat = lister_dossiers(
        recherche=request.GET.get("q", "").strip(),
        statut=request.GET.get("statut", ""),
        type_affaire=request.GET.get("type_affaire", ""),
        client_id=request.GET.get("client_id", ""),
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
    )
    return JsonResponse(resultat, status=200)


##@login_required
@require_GET
def api_detail_dossier(request, dossier_id):
    try:
        dossier = obtenir_dossier(dossier_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Dossier introuvable."}, status=404)
    return JsonResponse(dossier_vers_dict(dossier), status=200)


##@login_required
@require_http_methods(["POST"])
def api_creer_dossier(request):
    try:
        payload = json.loads(request.body)
        dossier = creer_dossier(payload, request.user)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Dossier créé avec succès.", "dossier": dossier_vers_dict(dossier)},
        status=201,
    )


##@login_required
@require_http_methods(["POST"])
def api_modifier_dossier(request, dossier_id):
    try:
        payload = json.loads(request.body)
        dossier = modifier_dossier(dossier_id, payload, request.user)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Dossier introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Dossier modifié avec succès.", "dossier": dossier_vers_dict(dossier)},
        status=200,
    )


##@login_required
@require_http_methods(["POST"])
def api_supprimer_dossier(request, dossier_id):
    try:
        supprimer_dossier(dossier_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Dossier introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)

    return JsonResponse({"message": "Dossier supprimé avec succès."}, status=200)


# ---------------------------------------------------------------------------
# Export CSV / Excel — respecte les mêmes filtres que le tableau (q, statut,
# type_affaire, client_id, date_debut, date_fin), sans pagination.
# ---------------------------------------------------------------------------

def _filtres_export(request):
    return {
        "recherche": request.GET.get("q", "").strip(),
        "statut": request.GET.get("statut", ""),
        "type_affaire": request.GET.get("type_affaire", ""),
        "client_id": request.GET.get("client_id", ""),
        "date_debut": request.GET.get("date_debut", ""),
        "date_fin": request.GET.get("date_fin", ""),
    }


##@login_required
""" @require_GET
def api_exporter_dossiers_csv(request):
    contenu = exporter_dossiers_csv(**_filtres_export(request))
    reponse = HttpResponse(contenu, content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = 'attachment; filename="dossiers.csv"'
    return reponse """


##@login_required
""" @require_GET
def api_exporter_dossiers_excel(request):
    classeur = exporter_dossiers_excel(**_filtres_export(request))
    reponse = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    reponse["Content-Disposition"] = 'attachment; filename="dossiers.xlsx"'
    classeur.save(reponse)
    return reponse """


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)

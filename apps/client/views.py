# client/views.py
"""
Contrôleur (vues) du module Client.
Rôle strict : décoder la requête HTTP, appeler le service, renvoyer une réponse.
Aucune logique métier ici -> tout est dans client/services/nom_affichage.py.
"""

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from client.models import Client
#from client.services import nom_affichage

#from client.services import client_service

# CORRECTION : On importe directement les fonctions autonomes du fichier services
from client.services import obtenir_client, lister_clients, creer_client, modifier_client, supprimer_client, client_vers_dict




##@login_required
def client_dashboard(request):
    """Rend le template unique du dashboard Client (tableau + modals intégrés)."""
    contexte = {
        "types_client": Client.ClientType.choices,
    }
    return render(request, "client/client_dashboard.html", contexte)


##@login_required
@require_GET
def api_lister_clients(request):
    """
    Endpoint AJAX consommé par client_dashboard.html.
    Query params : q (recherche), type, date_debut, date_fin, page, page_size
    """
    resultat = lister_clients(
        recherche=request.GET.get("q", "").strip(),
        type_client=request.GET.get("type", ""),
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
    )
    return JsonResponse(resultat, status=200)


##@login_required
@require_GET
def api_detail_client(request, client_id):
    try:
        client = obtenir_client(client_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Client introuvable."}, status=404)
    return JsonResponse(client_vers_dict(client), status=200)


##@login_required
@require_http_methods(["POST"])
def api_creer_client(request):
    try:
        payload = json.loads(request.body)
        client = creer_client(payload, request.user)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Client créé avec succès.", "client": client_vers_dict(client)},
        status=201,
    )


##@login_required
@require_http_methods(["POST"])
def api_modifier_client(request, client_id):
    try:
        payload = json.loads(request.body)
        client = modifier_client(client_id, payload, request.user)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Client introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Client modifié avec succès.", "client": client_vers_dict(client)},
        status=200,
    )


##@login_required
@require_http_methods(["POST"])
def api_supprimer_client(request, client_id):
    try:
        supprimer_client(client_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Client introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)

    return JsonResponse({"message": "Client supprimé avec succès."}, status=200)


# ---------------------------------------------------------------------------
# Export CSV / Excel — respecte les mêmes filtres que le tableau (q, type,
# date_debut, date_fin), mais exporte TOUS les résultats (pas de pagination).
# ---------------------------------------------------------------------------

def _filtres_export(request):
    return {
        "recherche": request.GET.get("q", "").strip(),
        "type_client": request.GET.get("type", ""),
        "date_debut": request.GET.get("date_debut", ""),
        "date_fin": request.GET.get("date_fin", ""),
    }


##@login_required
@require_GET
def api_exporter_clients_csv(request):
    contenu = exporter_clients_csv(**_filtres_export(request))
    reponse = HttpResponse(contenu, content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = 'attachment; filename="clients.csv"'
    return reponse


##@login_required
@require_GET
def api_exporter_clients_excel(request):
    classeur = exporter_clients_excel(**_filtres_export(request))
    reponse = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    reponse["Content-Disposition"] = 'attachment; filename="clients.xlsx"'
    classeur.save(reponse)
    return reponse


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)

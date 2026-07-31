import json
import pprint

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from notifications.models import SMSDetailDestinataire

from dossier.models import Dossier
from notifications.services import (
    agendas_disponibles_pour_sms, compteurs_statuts, lister_sms, obtenir_sms,
    creer_campagne_sms, modifier_sms,
    lister_fournisseurs, creer_fournisseur, modifier_fournisseur, supprimer_fournisseur,
)


@login_required
def notification_dashboard(request):
    resultat = lister_sms(page=1, page_size=10)
    contexte = {
        "agendas_disponibles": agendas_disponibles_pour_sms(),
        "resultats_initiaux": resultat["resultats"],
        "pagination_initiale": resultat["pagination"],
        #"compteurs": resultat["compteurs"],
        "compteurs": compteurs_statuts(),
        "dossiers": Dossier.objects.all().order_by('-date_ouverture')[:200],
        "statuts_sms": SMSDetailDestinataire.StatutSMS.choices,
    }
    #print("Le contexte Alerte --> ", contexte["resultats_initiaux"])
    #pprint.pprint(list(contexte["resultats_initiaux"])) # Force la conversion en liste pour l'affichage
    return render(request, "notifications/notification_dashboard.html", contexte)


@login_required
@require_GET
def api_lister_sms(request):
# Sécurisation des valeurs numériques pour éviter les crashs ValueError
    try:
        page = int(request.GET.get("page", 1))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = int(request.GET.get("page_size", 10))
    except (ValueError, TypeError):
        page_size = 10
    
    resultat = lister_sms(
        recherche=request.GET.get("q", "").strip(),
        statut=request.GET.get("statut", ""),
        dossier_id=request.GET.get("dossier_id", ""),
        date_filtre=request.GET.get("date_filtre", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
    )
    return JsonResponse(resultat, status=200)


@login_required
@require_http_methods(["POST"])
def api_creer_sms(request):
    try:
        payload = json.loads(request.body)
        groupes = creer_campagne_sms(payload, request.user)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": f"{len(groupes)} campagne(s) SMS créée(s) avec succès.", "redirect": None},
        status=201,
    )


@login_required
@require_http_methods(["POST"])
def api_modifier_sms(request, sms_id):
    try:
        payload = json.loads(request.body)
        detail = modifier_sms(sms_id, payload, request.user)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "SMS introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)

    from notifications.services import sms_vers_dict
    return JsonResponse({"message": "SMS modifié avec succès.", "sms": sms_vers_dict(detail)}, status=200)


@login_required
@require_GET
def api_detail_sms(request, sms_id):
    try:
        from notifications.services import sms_vers_dict
        return JsonResponse(sms_vers_dict(obtenir_sms(sms_id)), status=200)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "SMS introuvable."}, status=404)


# --- Fournisseurs SMS ---

@login_required
@require_GET
def api_lister_fournisseurs(request):
    return JsonResponse({"resultats": lister_fournisseurs()}, status=200)


@login_required
@require_http_methods(["POST"])
def api_creer_fournisseur(request):
    try:
        payload = json.loads(request.body)
        creer_fournisseur(payload)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    return JsonResponse({"message": "Fournisseur créé avec succès."}, status=201)


@login_required
@require_http_methods(["PUT"])
def api_modifier_fournisseur(request, fournisseur_id):
    try:
        payload = json.loads(request.body)
        provider = modifier_fournisseur(fournisseur_id, payload)
        
        # On retourne l'objet complet mis à jour
        return JsonResponse({
            "message": "Fournisseur modifié avec succès.",
            "fournisseur": {
                "id": str(provider.id),
                "nom": provider.nom,
                "sender_id": provider.sender_id,
                "base_url": provider.base_url,
                "api_key": provider.api_key,
                "is_default": provider.is_default,
                "is_active": provider.is_active,
            }
        }, status=200)

    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Fournisseur introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Format JSON invalide."}, status=400)


""" @login_required
@require_http_methods(["POST"])
def api_modifier_fournisseur(request, fournisseur_id):
    try:
        payload = json.loads(request.body)
        modifier_fournisseur(fournisseur_id, payload)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Fournisseur introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    return JsonResponse({"message": "Fournisseur modifié avec succès."}, status=200) """


@login_required
@require_http_methods(["POST"])
def api_supprimer_fournisseur(request, fournisseur_id):
    try:
        supprimer_fournisseur(fournisseur_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Fournisseur introuvable."}, status=404)
    return JsonResponse({"message": "Fournisseur supprimé avec succès."}, status=200)


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
import json
import pprint

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from notifications.models import SMSDetailDestinataire, ProviderSMS

from dossier.models import Dossier

from notifications.services import (
    agendas_disponibles_pour_sms, compteurs_statuts, lister_sms, obtenir_sms,
    creer_campagne_sms, modifier_sms,
    ProviderSMSProtegeError, creer_fournisseur, modifier_fournisseur, supprimer_fournisseur,
)

@login_required
def notification_dashboard(request):
    resultat = lister_sms(page=1, page_size=10)
    contexte = {
        "agendas_disponibles": agendas_disponibles_pour_sms(),
        "resultats_initiaux": resultat["resultats"],
        "pagination_initiale": resultat["pagination"],
        "compteurs": compteurs_statuts(),  # S'assure d'alimenter les cartes d'états
        "dossiers": Dossier.objects.all().order_by('-date_ouverture')[:200],
        "statuts_sms": SMSDetailDestinataire.StatutSMS.choices,
    }
    return render(request, "notifications/notification_dashboard.html", contexte)

@login_required
@require_GET
def api_lister_sms(request):
# Sécurisation des valeurs numériques pour éviter les crashs ValueError
    
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
        print("DEBUG PAYLOAD >>>", pprint.pformat(payload))
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
def api_lister_fournisseurs(request):
    fournisseurs_qs = ProviderSMS.objects.all().order_by('-is_default', 'nom')
    
    data = []
    for f in fournisseurs_qs:
        data.append({
            'id': f.id,
            'nom': f.nom,
            'sender_id': f.sender_id,
            'base_url': f.base_url,
            'api_key': f.api_key,
            'is_default': f.is_default,
            'is_active': f.is_active,
        })
    
    # Renvoyer sous la clé 'fournisseurs'
    return JsonResponse({'fournisseurs': data})

""" @login_required
@require_GET
def api_lister_fournisseurs(request):
    return JsonResponse({"resultats": lister_fournisseurs()}, status=200) """


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


@login_required
@require_http_methods(["POST"])
def api_supprimer_fournisseur(request, fournisseur_id):
    # Optionnel : permettre de passer un paramètre pour forcer la désactivation
    desactiver_si_bloque = request.POST.get('desactiver_si_bloque') == 'true'

    try:
        res = supprimer_fournisseur(fournisseur_id, desactiver_si_protege=desactiver_si_bloque)
        
        if res["action"] == "deactivated":
            return JsonResponse({
                "succes": True,
                "action": "deactivated",
                "message": f"Le fournisseur a été désactivé car {res['count']} envoi(s) SMS y sont rattachés."
            }, status=200)

        return JsonResponse({
            "succes": True,
            "action": "deleted",
            "message": "Fournisseur supprimé avec succès."
        }, status=200)

    except ObjectDoesNotExist:
        return JsonResponse({
            "succes": False,
            "erreur": "Fournisseur introuvable."
        }, status=404)

    except ValueError as e:
        return JsonResponse({
            "succes": False,
            "erreur": str(e)
        }, status=400)

    except ProviderSMSProtegeError as e:
        # C'est ici qu'on alimente la modale explicite pour le frontend !
        return JsonResponse({
            "succes": False,
            "erreur_protegee": True,
            "erreur": str(e),
            "count": e.count,
            "conseil": "Désactivez ce fournisseur ou conservez-le pour garder l'historique des envois SMS."
        }, status=409)  # 409 Conflict est le code HTTP adapté

""" @login_required
@require_http_methods(["POST"])
def api_supprimer_fournisseur(request, fournisseur_id):
    try:
        supprimer_fournisseur(fournisseur_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Fournisseur introuvable."}, status=404)
    return JsonResponse({"message": "Fournisseur supprimé avec succès."}, status=200) """





def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
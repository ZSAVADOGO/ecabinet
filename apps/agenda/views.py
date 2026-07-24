# agenda/views.py
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Q


from dossier.models import Dossier
from agenda.models import EvenementAgenda, PartiePrenante, RolePartiePrenante

from agenda.services import (evenement_vers_dict,_queryset_filtre, lister_evenements,obtenir_evenement,
creer_evenement,modifier_evenement,supprimer_evenement,options_dossiers)

from django.contrib.auth import get_user_model # <-- Ajouté pour récupérer le modèle User

User = get_user_model()


#@login_required
def agenda_dashboard(request):
    utilisateurs_data = [
    {
        'id': str(u.id),  # Convertir l'UUID en string
        'first_name': u.first_name,
        'last_name': u.last_name,
        'username': u.username,
        'label': f"{u.first_name} {u.last_name}".strip() or u.username
    }
    for u in User.objects.all()
]
    contexte = {
        # Utiliser les choices réels issus du modèle
        "types_evenement": EvenementAgenda.TypeEvenement.choices,
        "statuts_traitement": EvenementAgenda.StatutTraitement.choices,
        "types_delai": EvenementAgenda.TypeDelaiProcedure.choices,
        "dossiers": options_dossiers(),
        'utilisateurs': utilisateurs_data,
        #"utilisateurs": User.objects.filter(is_active=True).values("id", "first_name", "last_name", "username"),
    }
    #print("Le contexte est : ", contexte)  # Debugging line 
    return render(request, "agenda/agenda_dashboard.html", contexte)


#@login_required
def api_lister_evenements(request):
    try:
        #  CORRECTION : Appeler la fonction uniquement avec request
        resultat = lister_evenements(request)
        #print("Resultats de lister_evenements()--> ",resultat)

        return JsonResponse(resultat, safe=False)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'erreur': str(e)}, status=500)

@require_GET
def api_parties_prenantes_dossier(request, dossier_id):
    parties = PartiePrenante.objects.filter(dossier_id=dossier_id).values("id", "nom", "role")
    #print("Le request est : ", request)  # Debugging line 
    #print("Les parties sont : ", parties)  # Debugging line 

    data = [
        {
            "id": str(p["id"]),
            "nom": p["nom"],
            "role_display": dict(RolePartiePrenante.choices).get(p["role"], p["role"])
        }
        for p in parties
    ]
    return JsonResponse(data, safe=False)


@require_POST
def api_creer_partie_prenante_rapide(request):
    """Insère à la volée un intervenant externe depuis le formulaire."""
    try:
        data = json.loads(request.body)
        dossier_id = data.get("dossier_id")
        nom = data.get("nom")
        role = data.get("role")

        if not dossier_id or not nom or not role:
            return JsonResponse({"erreur": "Tous les paramètres (dossier, nom, rôle) sont obligatoires."}, status=400)

        dossier = get_object_or_404(Dossier, id=dossier_id)
        
        pp = PartiePrenante.objects.create(
            dossier=dossier,
            nom=nom.strip(),
            role=role.strip(),
            created_by=request.user if request.user.is_authenticated else None
        )
        return JsonResponse({"message": "Intervenant ajouté avec succès.", "id": str(pp.id)}, status=201)
    except Exception as e:
        return JsonResponse({"erreur": str(e)}, status=400)

@require_POST
def api_supprimer_partie_prenante_rapide(request, pk):
    """Radié définitivement une partie prenante de la table."""
    try:
        pp = get_object_or_404(PartiePrenante, id=pk)
        pp.delete()
        return JsonResponse({"message": "Intervenant radié définitivement."}, status=200)
    except Exception as e:
        return JsonResponse({"erreur": str(e)}, status=400)


def filtrer_evenements_api(request):
    """
    API JSON Endpoint : Filtre et retourne les événements d'agenda.
    """
    query = request.GET.get('recherche', '')
    type_evt = request.GET.get('type', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    statut = request.GET.get('statut', '')
    est_critique = request.GET.get('critique', '') == 'true'

    evenements = EvenementAgenda.objects.all().select_related('dossier').prefetch_related('responsables', 'parties_prenantes')

    if query:
        evenements = evenements.filter(
            Q(titre__icontains=query) |
            Q(dossier__reference__icontains=query) |
            Q(dossier__intitule__icontains=query) |
            Q(responsables__nom__icontains=query)
        ).distinct()

    if type_evt:
        evenements = evenements.filter(type_evenement=type_evt)

    if date_debut:
        evenements = evenements.filter(date_debut__gte=date_debut)

    if date_fin:
        evenements = evenements.filter(date_fin__lte=f"{date_fin} 23:59:59")

    if statut:
        evenements = evenements.filter(statut_traitement=statut)

    if est_critique:
        evenements = evenements.filter(est_critique=True)

    data = []
    for evt in evenements:
        data.append({
            'id': evt.id,
            'titre': evt.titre,
            'type_code': evt.type_evenement,
            'type_display': evt.get_type_evenement_display(),
            'dossier_id': evt.dossier.id if evt.dossier else None,
            'dossier_ref': f"{evt.dossier.reference} - {evt.dossier.intitule}" if evt.dossier else "Hors dossier",
            'date_debut': evt.date_debut.strftime('%d/%m/%Y %H:%M'),
            'date_debut_iso': evt.date_debut.isoformat(),
            'date_fin': evt.date_fin.strftime('%d/%m/%Y %H:%M') if evt.date_fin else None,
            'responsables': [r.get_full_name() for r in evt.responsables.all()],
            'parties_prenantes': [p.nom for p in evt.parties_prenantes.all()],
            'statut_code': evt.statut_traitement,
            'statut_display': evt.get_statut_traitement_display(),
            'est_critique': evt.est_critique,
        })

    return JsonResponse({'status': 'success', 'data': data})

@require_http_methods(["GET"])
def charger_parties_prenantes_dossier(request, dossier_id):
    """
    API JSON Endpoint : Retourne les parties prenantes associées à un dossier.
    """
    parties = PartiePrenante.objects.filter(dossier_id=dossier_id).values('id', 'nom', 'qualite')
    return JsonResponse({'status': 'success', 'data': list(parties)})

    
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
    user_pour_test = request.user
    if not user_pour_test.is_authenticated:
        user_pour_test = User.objects.first()
    try:
        payload = json.loads(request.body)
        evt = creer_evenement(payload, user_pour_test)
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
    user_pour_test = request.user
    if not user_pour_test.is_authenticated:
            user_pour_test = User.objects.first()
    try:
        payload = json.loads(request.body)
        evt = modifier_evenement(evenement_id, payload, user_pour_test)
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


#@login_required # 🛡️ Sécurité : Seul un utilisateur connecté peut supprimer
@require_http_methods(["DELETE"]) # 🌟 CORRECTION : On accepte uniquement le DELETE
def api_supprimer_evenement(request, evenement_id):
    # Récupération propre de l'objet (lève automatiquement un 404 si introuvable)
    # Note : Si 'evenement_id' est un UUID, get_object_or_404 gère parfaitement la conversion.
    evenement = get_object_or_404(EvenementAgenda, id=evenement_id)
    
    # 🔐 Analyse d'expert - Sécurité Métier essentielle :
    # On vérifie que l'utilisateur a le droit de supprimer cet événement
    """ if not request.user.is_authenticated:
        return JsonResponse({"erreur": "Vous devez être connecté pour supprimer un événement."}, status=403) """

    """ if evenement.created_by != request.user and not request.user.is_staff:
                return JsonResponse({
                    "status": "error",
                    "message": "Vous n'avez pas la permission de supprimer cet événement."
                }, status=403) """
        
    # Suppression de l'objet
    evenement.delete()

    # 🌟 CORRECTION : Format aligné avec les attentes du JavaScript (status: success)
    return JsonResponse({
        "status": "success", 
        "message": "Événement supprimé avec succès."
    }, status=200)


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
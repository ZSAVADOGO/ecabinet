# agenda/views.py
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Q

from dossier.models import Chambre, Tribunal

from notifications.models import SMSDetailDestinataire


from dossier.models import Dossier
from agenda.models import EvenementAgenda, PartiePrenante, RolePartiePrenante

from agenda.services import (evenement_vers_dict, lister_evenements,obtenir_evenement,
creer_evenement,modifier_evenement_agenda,options_dossiers)

from django.contrib.auth import get_user_model # <-- Ajouté pour récupérer le modèle User

User = get_user_model()


@login_required
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

         # AJOUT INDISPENSABLE : Alimentation des listes du Modal HTML
        "tribunaux": Tribunal.objects.all().order_by('ville', 'nom', 'code'),
        "chambres": Chambre.objects.all().order_by('libelle'),

        #"utilisateurs": User.objects.filter(is_active=True).values("id", "first_name", "last_name", "username"),
    }
    #print("Le contexte est : ", contexte)  # Debugging line 
    return render(request, "agenda/agenda_dashboard.html", contexte)

@login_required
@require_GET
def charger_juridiction_evenement_ou_dossier(request):
    """
    API JSON Endpoint : Retourne le tribunal et la chambre associés à un événement ou un dossier (repli).
    """
    evenement_id = request.GET.get('evenement_id', '').strip()
    dossier_id = request.GET.get('dossier_id', '').strip()
    
    tribunal_id = None
    chambre_id = None

    # 1. Priorité absolue à l'événement existant (Mode Édition)
    if evenement_id:
        try:
            evt = EvenementAgenda.objects.get(id=evenement_id)
            if evt.tribunal_id:
                tribunal_id = str(evt.tribunal_id)
                chambre_id = str(evt.chambre_id) if evt.chambre_id else None
        except EvenementAgenda.DoesNotExist:
            pass

    # 2. Système de repli sur le Dossier (Mode Création ou si l'événement n'a pas de spécificité)
    if not tribunal_id and dossier_id:
        try:
            dossier = Dossier.objects.get(id=dossier_id)
            tribunal_id = str(dossier.tribunal_id) if dossier.tribunal_id else None
            chambre_id = str(dossier.chambre_id) if dossier.chambre_id else None
        except Dossier.DoesNotExist:
            pass

    # 3. Retour de la structure de données propre
    return JsonResponse({
        'status': 'success',
        'data': {
            'tribunal_id': tribunal_id,
            'chambre_id': chambre_id
        }
    })


@login_required
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

@login_required
def api_liste_sms_evenement(request, evenement_id):
    """
    Retourne la liste des SMS rattachés à un événement sous forme JSON propre.
    """
    try:
        details = SMSDetailDestinataire.objects.filter(
            group_envoi__evenement_agenda_id=evenement_id
        ).select_related('group_envoi').order_by('-group_envoi__created_at')

        data = [{
            'id': str(d.id),
            'telephone': d.telephone,
            'destinataire_nom': d.destinataire_nom or d.telephone,
            'destinataire_role': d.destinataire_role or 'Partie',
            'status': d.status,
            'status_display': d.get_status_display(),
            'message_text': d.group_envoi.message_text if d.group_envoi else '',
            'created_at': d.group_envoi.created_at.strftime('%d/%m/%Y %H:%M') if d.group_envoi else '',
        } for d in details]

        return JsonResponse({'status': 'success', 'resultats': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import EvenementAgenda

def api_parties_prenantes_evenement(request, evenement_id):
    """
    Retourne la liste combinée des destinataires potentiels pour un événement :
    1. Responsables de l'événement (ManyToMany User)
    2. Avocat référent du dossier (ForeignKey User)
    3. Client du dossier (ForeignKey Client)
    4. Partie adverse (Texte)
    """
    try:
        # 1. Récupération de l'événement avec optimisation d'accès au dossier/client
        evenement = get_object_or_404(
            EvenementAgenda.objects.select_related('dossier__client', 'dossier__avocat_referent')
                                   .prefetch_related('responsables'),
            id=evenement_id
        )
        
        resultats = []
        ids_ajoutes = set()  # Pour éviter les doublons si un utilisateur a plusieurs rôles

        # -------------------------------------------------------------
        # A. RESPONSABLES DE L'ÉVÉNEMENT (EvenementAgenda.responsables)
        # -------------------------------------------------------------
        for resp in evenement.responsables.all():
            nom = f"{resp.first_name} {resp.last_name}".strip() or resp.username
            tel = getattr(resp, 'telephone_direct', '') or getattr(resp, 'phone', '') or ''
            resultats.append({
                'id': f"user_{resp.id}",
                'nom': nom,
                'role': "Responsable Événement",
                'telephone': tel,
                'is_responsable': True
            })
            ids_ajoutes.add(f"user_{resp.id}")

        # Si un dossier est lié à l'événement
        dossier = evenement.dossier
        if dossier:
            # -------------------------------------------------------------
            # B. AVOCAT RÉFÉRENT DU DOSSIER (Dossier.avocat_referent)
            # -------------------------------------------------------------
            if dossier.avocat_referent:
                ref = dossier.avocat_referent
                ref_key = f"user_{ref.id}"
                if ref_key not in ids_ajoutes:
                    nom = f"{ref.first_name} {ref.last_name}".strip() or ref.username
                    tel = getattr(ref, 'telephone', '') or getattr(ref, 'phone', '') or ''
                    resultats.append({
                        'id': ref_key,
                        'nom': nom,
                        'role': "Avocat Référent (Dossier)",
                        'telephone': tel,
                        'is_responsable': False
                    })
                    ids_ajoutes.add(ref_key)

            # -------------------------------------------------------------
            # C. CLIENT DU DOSSIER (Dossier.client)
            # -------------------------------------------------------------
            if dossier.client:
                client = dossier.client
                nom_client = getattr(client, 'nom_complet', None) or getattr(client, 'nom', str(client))
                tel_client = getattr(client, 'telephone', '') or getattr(client, 'telephone_mobile', '') or ''
                resultats.append({
                    'id': f"client_{client.id}",
                    'nom': nom_client,
                    'role': "Client",
                    'telephone': tel_client,
                    'is_responsable': False
                })

            # -------------------------------------------------------------
            # D. PARTIE ADVERSE (Dossier.partie_adverse)
            # -------------------------------------------------------------
            if dossier.partie_adverse:
                resultats.append({
                    'id': f"adverse_{dossier.id}",
                    'nom': dossier.partie_adverse,
                    'role': "Partie Adverse",
                    'telephone': '',  # Souvent non renseigné direct
                    'is_responsable': False
                })

        return JsonResponse(resultats, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
""" @login_required
def api_parties_prenantes_evenement(request, evenement_id):
    evenement = get_object_or_404(EvenementAgenda, id=evenement_id)
    dossier = evenement.dossier  # Récupération du dossier associé
    
    resultats = []

    # 1. Ajouter le Responsable du dossier (S'il existe)
    if dossier and dossier.responsable:
        resp = dossier.responsable
        resultats.append({
            'id': f"resp_{resp.id}",
            'nom': f"{resp.first_name} {resp.last_name}".strip() or resp.username,
            'role': "Responsable du dossier",
            'telephone': getattr(resp, 'telephone', '') or "Sans N°",
            'is_responsable': True
        })

    # 2. Ajouter les autres Parties Prenantes / Contacts
    if dossier:
        for party in dossier.parties_prenantes.all():
            resultats.append({
                'id': f"partie_{party.id}",
                'nom': party.nom_complet,
                'role': party.get_role_display() if hasattr(party, 'get_role_display') else "Partie Prenante",
                'telephone': party.telephone or "Sans N°",
                'is_responsable': False
            })

    return JsonResponse(resultats, safe=False) """

""" 
@login_required
def api_parties_prenantes_evenement(request, evenement_id):
    try:
        evt = get_object_or_404(EvenementAgenda, id=evenement_id)
        
        if not evt.dossier_id:
            return JsonResponse([], safe=False)

        parties = PartiePrenante.objects.filter(dossier_id=evt.dossier_id)
        
        data = [{
            "id": str(p.id),
            "nom": p.nom,
            "telephone": getattr(p, 'telephone', ''),
            "role_display": dict(RolePartiePrenante.choices).get(p.role, p.role)
        } for p in parties]

        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500) """
    
""" 
@login_required
def api_liste_sms_evenement(request, evenement_id):
   
    evt = get_object_or_404(EvenementAgenda, id=evenement_id)
    
    # Récupération via le ForeignKey related_name 'campagnes_sms'
    details = SMSDetailDestinataire.objects.filter(
        group_envoi__evenement_agenda=evt
    ).select_related('group_envoi').order_by('-group_envoi__created_at')

    data = [{
        'id': str(d.id),
        'telephone': d.telephone,
        'destinataire_nom': d.destinataire_nom,
        'destinataire_role': d.destinataire_role,
        'status': d.status,
        'status_display': d.get_status_display(),
        'message_text': d.group_envoi.message_text,
        'created_at': d.group_envoi.created_at.isoformat(),
    } for d in details]

    return JsonResponse({'resultats': data}) """

@login_required
@require_GET
def charger_responsables_dossier(request, dossier_id):
    """
    API JSON Endpoint : Retourne les responsables par défaut d'un dossier (Avocat référent).
    """
    try:
        dossier = Dossier.objects.select_related('avocat_referent').get(id=dossier_id)
        responsables = []
        
        if dossier.avocat_referent:
            responsables.append({
                'id': str(dossier.avocat_referent.id),
                'nom': f"{dossier.avocat_referent.first_name} {dossier.avocat_referent.last_name}".strip() or dossier.avocat_referent.username
            })
        
        return JsonResponse({'status': 'success', 'data': responsables})
    except Dossier.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Dossier introuvable'}, status=404)


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

@login_required
@require_http_methods(["POST"])
def api_modifier_evenement_agenda(request, event_id):
    """
    Vue d'API dédiée à la modification des événements d'agenda du cabinet.
    """
    try:
        payload = json.loads(request.body)
        evenement = modifier_evenement_agenda(event_id, payload, request.user)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Événement d'agenda introuvable."}, status=404)
    except ValidationError as exc:
        msg = exc.messages[0] if hasattr(exc, 'messages') else str(exc)
        return JsonResponse({"erreur": msg}, status=400)

    return JsonResponse({
        "message": "Événement mis à jour avec succès.",
        "evenement": {
            "id": evenement.id,
            "titre": evenement.titre,
            "date_heure": evenement.date_heure.isoformat() if evenement.date_heure else None,
            "statut_traitement": evenement.statut_traitement,
            "critique": evenement.critique
        }
    }, status=200)

#@login_required
""" @require_http_methods(["POST"])
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
    ) """


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
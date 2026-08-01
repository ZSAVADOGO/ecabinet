"""
Couche service du module Notifications (SMS).
"""
import uuid
import requests
import logging
logger = logging.getLogger(__name__)
from decimal import Decimal

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

from notifications.models import ProviderSMS, SMSGroupEnvoi, SMSDetailDestinataire
from agenda.models import EvenementAgenda
from dossier.models import Dossier
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.deletion import ProtectedError

from datetime import timedelta

CHAMPS_RECHERCHE = ["telephone", "group_envoi__message_text", "group_envoi__evenement_agenda__dossier__reference"]



def normaliser_telephone_bf(numero: str, indicatif_defaut: str = "+226") -> str:
    if not numero:
        return ""

    # 1. Nettoyage : retirer les espaces, tirets et points
    num = str(numero).strip().replace(" ", "").replace("-", "").replace(".", "")

    # 2. Cas où le numéro commence déjà par '+' (ex: +22670250633) -> On conserve tel quel
    if num.startswith("+"):
        return num

    # 3. Cas où l'utilisateur commence par '226' sans '+' (ex: 22670250633) -> On ajoute '+'
    if num.startswith("226"):
        return f"+{num}"

    # 4. Cas où c'est un numéro local à 8 chiffres (ex: 70250633) -> On ajoute '+226'
    if len(num) == 8 and num.isdigit():
        return f"{indicatif_defaut}{num}"

    # Fallback pour les autres cas (ex: numéros internationaux déjà saisis sans +)
    return f"+{num}"

# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------

def sms_vers_dict(detail: SMSDetailDestinataire) -> dict:
    groupe = detail.group_envoi
    dossier = groupe.evenement_agenda.dossier if (groupe.evenement_agenda and groupe.evenement_agenda.dossier_id) else None
    return {
        "id": str(detail.id),
        "telephone": detail.telephone,

        "destinataire_nom": detail.destinataire_nom,
        "destinataire_role": detail.destinataire_role,

        "statut": detail.status,
        "statut_libelle": detail.get_status_display(),
        "message": groupe.message_text,
        "modifiable": groupe.statut == SMSGroupEnvoi.StatutGlobal.EN_ATTENTE and detail.status == SMSDetailDestinataire.StatutSMS.PENDING,
        "dossier_reference": dossier.reference if dossier else None,
        "dossier_intitule": dossier.intitule if dossier else None,
        "agenda_titre": groupe.evenement_agenda.titre if groupe.evenement_agenda_id else None,
        "programme_pour": groupe.send_at.isoformat() if groupe.send_at else None,
        "envoye_le": detail.send_at.strftime("%d/%m/%Y %H:%M") if detail.send_at else None,
        "groupe_id": str(groupe.id),
    }


def agendas_disponibles_pour_sms():
    """
    Alimente le <select> du wizard : agenda + ses responsables/parties prenantes notifiables.
    """
    resultats = []
    evenements = (
        EvenementAgenda.objects
        .select_related('dossier', 'tribunal', 'chambre')
        .prefetch_related('responsables', 'parties_prenantes')
        .order_by('-date_heure')[:200]  # fenêtre raisonnable, évite un select géant
    )
    for e in evenements:
        responsables = [
            {"nom": (u.get_full_name() or u.username), "role": "Responsable", "telephone": getattr(u, 'telephone_direct', '') or ''}
            for u in e.responsables.all()
        ]
        parties = [
            {"nom": p.nom, "role": p.get_role_display(), "telephone": p.telephone or ''}
            for p in e.parties_prenantes.all() if p.notifiable
        ]
        resultats.append({
            "id": str(e.id),
            "titre": e.titre,
            "date_affichee": e.date_heure.strftime("%d/%m/%Y %H:%M"),
            "type_libelle": e.get_type_display(),
            "tribunal": e.tribunal.code if e.tribunal_id else None,
            "chambre": e.chambre.libelle if e.chambre_id else None,
            "dossier_reference": e.dossier.reference if e.dossier_id else None,
            "dossier_intitule": e.dossier.intitule if e.dossier_id else None,
            "responsables": responsables,
            "parties_prenantes": parties,
        })
    return resultats

def compteurs_statuts(queryset=None):
    if queryset is None:
        queryset = SMSDetailDestinataire.objects.all()

    # Une seule agrégation SQL groupée par 'status'
    counts = dict(
        queryset.values('status')
        .annotate(total=Count('id'))
        .values_list('status', 'total')
    )

    return {
        "pending": counts.get('PENDING', 0),
        "delivery_success": counts.get('DELIVERY_SUCCESS', 0),
        "delivery_failed": counts.get('DELIVERY_FAILED', 0),
        "expired": counts.get('EXPIRED', 0),
    }

# ---------------------------------------------------------------------------
# Listing paginé
# ---------------------------------------------------------------------------

def lister_sms(recherche="", statut="", dossier_id="", date_filtre="", page=1, page_size=10):
    qs = SMSDetailDestinataire.objects.select_related(
        'group_envoi', 
        'group_envoi__evenement_agenda', 
        'group_envoi__evenement_agenda__dossier'
    )

    # 1. Filtre Recherche textuelle
    if recherche:
        q = Q()
        for champ in CHAMPS_RECHERCHE:
            q |= Q(**{f"{champ}__icontains": recherche})
        qs = qs.filter(q)

    # 2. Filtre Dossier
    if dossier_id:
        qs = qs.filter(group_envoi__evenement_agenda__dossier_id=dossier_id)

    # 3. Filtre Date Rapide
    if date_filtre:
        aujourdhui = timezone.now().date()
        if date_filtre == 'today':
            qs = qs.filter(group_envoi__created_at__date=aujourdhui)
        elif date_filtre == 'this_week':
            debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())
            qs = qs.filter(group_envoi__created_at__date__gte=debut_semaine)
        elif date_filtre == 'this_month':
            qs = qs.filter(
                group_envoi__created_at__year=aujourdhui.year,
                group_envoi__created_at__month=aujourdhui.month
            )

    # 4. Calcul des compteurs (Sur la période/recherche sélectionnée, AVANT le filtre de statut)
    compte_raw = dict(
        qs.values('status')
        .annotate(total=Count('id'))
        .values_list('status', 'total')
    )
    compteurs = {
        "pending": compte_raw.get('PENDING', 0),
        "delivery_success": compte_raw.get('DELIVERY_SUCCESS', 0),
        "delivery_failed": compte_raw.get('DELIVERY_FAILED', 0),
        "expired": compte_raw.get('EXPIRED', 0),
    }

    # 5. Filtre Statut (Appliqué uniquement aux lignes affichées dans le tableau)
    if statut:
        qs = qs.filter(status=statut)

    # 6. Pagination
    qs = qs.order_by('-group_envoi__created_at')
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    return {
        "resultats": [sms_vers_dict(d) for d in page_obj.object_list],
        "compteurs": compteurs,
        "pagination": {
            "page_courante": page_obj.number,
            "nb_pages": paginator.num_pages,
            "nb_resultats": paginator.count,
            "page_size": page_size,
            "a_precedent": page_obj.has_previous(),
            "a_suivant": page_obj.has_next(),
        },
    }


def obtenir_sms(detail_id) -> SMSDetailDestinataire:
    return SMSDetailDestinataire.objects.select_related('group_envoi').get(pk=detail_id)


# ---------------------------------------------------------------------------
# Création d'une campagne (immédiate et/ou programmée sur plusieurs dates)
# ---------------------------------------------------------------------------

""" def creer_campagne_sms(payload: dict, utilisateur) -> list:
    #print("Le paylod recu -->", payload, "L'utilisateur -->", utilisateur)
    numeros = [n.strip() for n in payload.get("numeros", []) if n and n.strip()]

     # Récupération sécurisée des listes reçues
    destinataire_noms = payload.get("nomDestinataire", [])
    destinataire_roles = payload.get("roleDestinataire", [])

    message = (payload.get("message") or "").strip()
    if not numeros:
        raise ValidationError("Au moins un numéro de téléphone est requis.")
    if not message:
        raise ValidationError("Le message ne peut pas être vide.")

    evenement_id = payload.get("evenement_id") or None
    dates_programmees = payload.get("dates_programmees") or []
    immediat = bool(payload.get("immediat"))

    if not immediat and not dates_programmees:
        raise ValidationError("Choisissez un envoi immédiat, une date ultérieure, ou les deux.")

    provider = ProviderSMS.objects.filter(is_default=True, is_active=True).first()
    print("DEBUG PROVIDER Actif est >>>", provider)
    if not provider:
        raise ValidationError("Aucun fournisseur SMS actif n'est configuré par défaut.")


    groupes_crees = []

    with transaction.atomic():
        if immediat:
            groupe = _creer_groupe(provider, evenement_id, utilisateur, message, numeros, destinataire_noms, destinataire_roles, envoyer_at=timezone.now())
            _envoyer_groupe(groupe)
            groupes_crees.append(groupe)

        for date_str in dates_programmees:
            envoyer_at = _parse_datetime_local(date_str)
            groupe = _creer_groupe(provider, evenement_id, utilisateur, message, numeros, destinataire_noms, destinataire_roles, envoyer_at=envoyer_at)
            groupes_crees.append(groupe)

    return groupes_crees


def _creer_groupe(provider, evenement_id, utilisateur, message, numeros, destinataire_noms, destinataire_roles, envoyer_at):
    print(f"DEBUG CREATION GROUPE >>> provider={provider}, evenement_id={evenement_id}, utilisateur={utilisateur}, message={message}, envoyer_at={envoyer_at}")
    groupe = SMSGroupEnvoi.objects.create(
        provider=provider,
        evenement_agenda_id=evenement_id,
        expediteur=utilisateur,
        message_text=message,
        send_at=envoyer_at,
        statut=SMSGroupEnvoi.StatutGlobal.EN_ATTENTE,
    )

    destinataires = []
    for i, numero in enumerate(numeros):
        # Récupération indexée sécurisée (fallback si la liste est plus courte que les numéros)
        nom = destinataire_noms[i] if i < len(destinataire_noms) else "Destinataire Inconnu"
        role = destinataire_roles[i] if i < len(destinataire_roles) else "Aucun"

        destinataires.append(
            SMSDetailDestinataire(
                group_envoi=groupe, 
                telephone=numero, 
                expediteur=groupe.expediteur, 
                destinataire_nom=nom, 
                destinataire_role=role,
                status=SMSDetailDestinataire.StatutSMS.PENDING.value
            )
        )

    SMSDetailDestinataire.objects.bulk_create(destinataires)
    return groupe """

def creer_campagne_sms(payload: dict, utilisateur) -> list:
    # 💡 1. EXTRACTION ET NORMALISATION DES NUMÉROS
    numeros_bruts = payload.get("numeros", [])
    numeros = [
        normaliser_telephone_bf(n) 
        for n in numeros_bruts 
        if n and str(n).strip()
    ]

    # Récupération sécurisée des listes reçues
    destinataire_noms = payload.get("nomDestinataire", [])
    destinataire_roles = payload.get("roleDestinataire", [])

    message = (payload.get("message") or "").strip()
    
    # Validation après normalisation
    if not numeros:
        raise ValidationError("Au moins un numéro de téléphone valide est requis.")
    if not message:
        raise ValidationError("Le message ne peut pas être vide.")

    evenement_id = payload.get("evenement_id") or None
    dates_programmees = payload.get("dates_programmees") or []
    immediat = bool(payload.get("immediat"))

    if not immediat and not dates_programmees:
        raise ValidationError("Choisissez un envoi immédiat, une date ultérieure, ou les deux.")

    provider = ProviderSMS.objects.filter(is_default=True, is_active=True).first()
    print("DEBUG PROVIDER Actif est >>>", provider)
    if not provider:
        raise ValidationError("Aucun fournisseur SMS actif n'est configuré par défaut.")

    groupes_crees = []

    with transaction.atomic():
        if immediat:
            # Transmet la liste 'numeros' dont tous les éléments ont été formatés avec '+226'
            groupe = _creer_groupe(provider, evenement_id, utilisateur, message, numeros, destinataire_noms, destinataire_roles, envoyer_at=timezone.now())
            _envoyer_groupe(groupe)
            groupes_crees.append(groupe)

        for date_str in dates_programmees:
            envoyer_at = _parse_datetime_local(date_str)
            groupe = _creer_groupe(provider, evenement_id, utilisateur, message, numeros, destinataire_noms, destinataire_roles, envoyer_at=envoyer_at)
            groupes_crees.append(groupe)

    return groupes_crees


def _creer_groupe(provider, evenement_id, utilisateur, message, numeros, destinataire_noms, destinataire_roles, envoyer_at):
    print(f"DEBUG CREATION GROUPE >>> provider={provider}, evenement_id={evenement_id}, utilisateur={utilisateur}, message={message}, envoyer_at={envoyer_at}")
    groupe = SMSGroupEnvoi.objects.create(
        provider=provider,
        evenement_agenda_id=evenement_id,
        expediteur=utilisateur,
        message_text=message,
        send_at=envoyer_at,
        statut=SMSGroupEnvoi.StatutGlobal.EN_ATTENTE,
    )

    destinataires = []
    for i, numero in enumerate(numeros):
        # Récupération indexée sécurisée
        nom = destinataire_noms[i] if i < len(destinataire_noms) else "Destinataire Inconnu"
        role = destinataire_roles[i] if i < len(destinataire_roles) else "Aucun"

        destinataires.append(
            SMSDetailDestinataire(
                group_envoi=groupe, 
                telephone=numero,  # <-- Enregistre directement le numéro formaté '+226...' en base !
                expediteur=groupe.expediteur, 
                destinataire_nom=nom, 
                destinataire_role=role,
                status=SMSDetailDestinataire.StatutSMS.PENDING.value
            )
        )

    SMSDetailDestinataire.objects.bulk_create(destinataires)
    return groupe

""" 
def _envoyer_groupe(groupe: SMSGroupEnvoi):
    print(f"DEBUG ENVOI GROUPE >>> provider={groupe.provider}, message={groupe.message_text}")
    try:
        # 1. Numéros déjà au format international (+226...)
        telephones = list(groupe.details.values_list("telephone", flat=True))

        # 2. Body JSON exact attendu par l'API
        payload = {
            "from": groupe.provider.sender_id,
            "text": groupe.message_text,
            "to": telephones,
        }

        # 3. Date d'envoi programmée (Format strict : "13:45 29012026")
        if groupe.send_at and groupe.send_at > timezone.now():
            payload["send_at"] = groupe.send_at.strftime("%H:%M %d%m%Y")

        # 4. Construction de l'URL propre (ex: https://www.aqilas.com/api/v1/sms)
        base_url = groupe.provider.base_url.rstrip('/')
        url_endpoint = f"{base_url}/sms"

        # 5. Entêtes avec le BON nom de Token (X-AUTH-TOKEN)
        api_token = groupe.provider.api_key.strip() if groupe.provider.api_key else ""
        headers = {
            "X-AUTH-TOKEN": api_token,  # <-- C'est cette clé exacte que l'API exige !
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # 6. Envoi de la requête
        reponse = requests.post(
            url_endpoint,
            headers=headers,
            json=payload,
            timeout=10,
        )

        print(f"DEBUG REPONSE API AQILAS >>> status_code={reponse.status_code}, content={reponse.text}")
        reponse.raise_for_status()
        donnees = reponse.json()

        # Enregistrement du succès
        groupe.bulk_id = donnees.get("bulk_id") or donnees.get("id")
        groupe.statut = SMSGroupEnvoi.StatutGlobal.ENVOYE
        groupe.save(update_fields=["bulk_id", "statut"])

    except Exception as exc:
        groupe.statut = SMSGroupEnvoi.StatutGlobal.ECHEC
        groupe.save(update_fields=["statut"])
        groupe.details.update(status=SMSDetailDestinataire.StatutSMS.DELIVERY_FAILED)
        
        erreur_detail = exc.response.text if hasattr(exc, 'response') and exc.response else str(exc)
        logging.getLogger(__name__).error(f"Échec envoi SMS groupe {groupe.id} : {erreur_detail}") """

def _envoyer_groupe(groupe: SMSGroupEnvoi):
    print(f"DEBUG ENVOI GROUPE >>> provider={groupe.provider}, message={groupe.message_text}")
    try:
        # 1. Extraction des numéros au format international (+226...)
        telephones = list(groupe.details.values_list("telephone", flat=True))

        # 2. Construction du payload conforme à Aqilas
        payload = {
            "from": groupe.provider.sender_id,
            "text": groupe.message_text,
            "to": telephones,
        }

        # 3. Date d'envoi programmée si elle est dans le futur
        if groupe.send_at and groupe.send_at > timezone.now():
            payload["send_at"] = groupe.send_at.strftime("%H:%M %d%m%Y")

        # 4. Preparation de l'URL et des entêtes avec X-AUTH-TOKEN
        base_url = groupe.provider.base_url.rstrip('/')
        url_endpoint = f"{base_url}/sms"
        api_token = groupe.provider.api_key.strip() if groupe.provider.api_key else ""

        headers = {
            "X-AUTH-TOKEN": api_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # 5. Envoi HTTP
        reponse = requests.post(url_endpoint, headers=headers, json=payload, timeout=10)
        reponse.raise_for_status()
        
        # 6. RECUPERATION DE LA REPONSE JSON AQILAS
        donnees = reponse.json()
        print(f"DEBUG REPONSE API AQILAS >>> {donnees}")

        # Exemple de réponse :
        # {"success": true, "message": "SMS ENVOYÉS", "bulk_id": "ffe9b685-...", "cost": 10, "currency": "XOF"}
        if donnees.get("success"):
            # A. Actualisation du Groupe (SMSGroupEnvoi)
            groupe.bulk_id = donnees.get("bulk_id")
            #groupe.cost = donnees.get("cost")
            groupe.currency = donnees.get("currency", "XOF")
            groupe.statut = SMSGroupEnvoi.StatutGlobal.ENVOYE

            cout_api = donnees.get("cost")
            groupe.cost = Decimal(str(cout_api)) if cout_api is not None else None

            # Sauvegarde explicite des champs du groupe
            groupe.save(update_fields=["bulk_id", "cost", "currency", "statut"])

            # B. Actualisation des Destinataires Individuels (SMSDetailDestinataire)
            # Puisque le message est accepté et en cours d'acheminement par l'opérateur :
            groupe.details.update(
                status=SMSDetailDestinataire.StatutSMS.PENDING.value,
                updated_at=timezone.now()
            )
        else:
            # Si success = False dans le JSON renvoyé par l'API
            _marquer_groupe_en_echec(groupe)

    except Exception as exc:
        _marquer_groupe_en_echec(groupe)
        erreur_detail = exc.response.text if hasattr(exc, 'response') and exc.response else str(exc)
        logger.error(f"Échec envoi SMS groupe {groupe.id} : {erreur_detail}")


def _marquer_groupe_en_echec(groupe: SMSGroupEnvoi):
    """Helper pour basculer le groupe et ses destinataires en ÉCHEC."""
    groupe.statut = SMSGroupEnvoi.StatutGlobal.ECHEC
    groupe.save(update_fields=["statut"])
    groupe.details.update(
        status=SMSDetailDestinataire.StatutSMS.DELIVERY_FAILED.value,
        updated_at=timezone.now()
    )


def recalculer_statut_groupe(groupe: SMSGroupEnvoi):
    """
    À appeler après réception d'un webhook/callback du fournisseur mettant à jour
    le statut individuel d'un ou plusieurs destinataires.
    """
    statuts = list(groupe.details.values_list('status', flat=True))
    if not statuts:
        return
    if all(s == SMSDetailDestinataire.StatutSMS.DELIVERY_SUCCESS for s in statuts):
        groupe.statut = SMSGroupEnvoi.StatutGlobal.TERMINE
    elif all(s in (SMSDetailDestinataire.StatutSMS.DELIVERY_FAILED, SMSDetailDestinataire.StatutSMS.EXPIRED) for s in statuts):
        groupe.statut = SMSGroupEnvoi.StatutGlobal.ECHEC
    elif any(s == SMSDetailDestinataire.StatutSMS.DELIVERY_SUCCESS for s in statuts):
        groupe.statut = SMSGroupEnvoi.StatutGlobal.PARTIEL
    groupe.save(update_fields=["statut"])


def modifier_sms(detail_id, payload: dict, utilisateur) -> SMSDetailDestinataire:
    detail = obtenir_sms(detail_id)
    groupe = detail.group_envoi

    if groupe.statut != SMSGroupEnvoi.StatutGlobal.EN_ATTENTE or detail.status != SMSDetailDestinataire.StatutSMS.PENDING:
        raise ValidationError("Ce SMS a déjà été envoyé ou traité, il ne peut plus être modifié.")

    if "telephone" in payload:
        detail.telephone = payload["telephone"]
        detail.save(update_fields=["telephone"])

    if "message" in payload:
        groupe.message_text = payload["message"]
        groupe.save(update_fields=["message_text"])

    if "send_at" in payload and payload["send_at"]:
        groupe.send_at = _parse_datetime_local(payload["send_at"])
        groupe.save(update_fields=["send_at"])

    return detail


def _parse_datetime_local(valeur: str):
    """Parse une valeur d'<input type='datetime-local'> (ex: '2026-08-05T14:30')."""
    try:
        return timezone.make_aware(datetime.strptime(valeur, "%Y-%m-%dT%H:%M"))
    except (ValueError, TypeError):
        raise ValidationError(f"Date/heure invalide : {valeur}")


# ---------------------------------------------------------------------------
# Fournisseurs SMS
# ---------------------------------------------------------------------------

def fournisseur_vers_dict(p: ProviderSMS) -> dict:
    return {
        "id": str(p.id), "nom": p.nom, "sender_id": p.sender_id,
        "base_url": p.base_url, "is_default": p.is_default, "is_active": p.is_active,
        # api_key volontairement absent : ne jamais exposer la clé au frontend
    }


def lister_fournisseurs():
    return [fournisseur_vers_dict(p) for p in ProviderSMS.objects.all().order_by('-is_default', 'nom')]


def creer_fournisseur(payload: dict) -> ProviderSMS:
    _valider_payload_fournisseur(payload)
    return ProviderSMS.objects.create(
        nom=payload["nom"],
        sender_id=payload.get("sender_id", "CABINET"),
        base_url=payload["base_url"],
        api_key=payload["api_key"],
        is_default=bool(payload.get("is_default")),
    )

def modifier_fournisseur(fournisseur_id, payload: dict) -> ProviderSMS:
    print("Le payload recu -->", payload, "L'id -->", fournisseur_id)
    with transaction.atomic():
        provider = ProviderSMS.objects.get(pk=fournisseur_id)
        
        provider.nom = payload.get("nom", provider.nom)
        provider.sender_id = payload.get("sender_id", provider.sender_id)
        provider.base_url = payload.get("base_url", provider.base_url)
        
        # Mettre à jour uniquement si fourni
        if payload.get("api_key"):
            provider.api_key = payload["api_key"]
            
        if "is_default" in payload:
            provider.is_default = bool(payload["is_default"])
            
        if "is_active" in payload:
            provider.is_active = bool(payload["is_active"])

        # CORRECTION ICI : fournisseur_id au lieu de provider_id
        if provider.is_default:
            ProviderSMS.objects.exclude(pk=fournisseur_id).update(is_default=False)

        provider.full_clean()
        provider.save()
        return provider

class ProviderSMSProtegeError(Exception):
    """Exception personnalisée pour capturer le cas où le provider est lié à d'autres objets."""
    def __init__(self, message, count=0):
        super().__init__(message)
        self.count = count

@transaction.atomic
def supprimer_fournisseur(fournisseur_id, desactiver_si_protege=False):
    """
    Supprime un ProviderSMS par son ID.
    Renoie True si supprimé, False si désactivé (si desactiver_si_protege=True).
    Lève ObjectDoesNotExist ou ProviderSMSProtegeError en cas de blocage.
    """
    try:
        provider = ProviderSMS.objects.select_for_update().get(pk=fournisseur_id)
    except ProviderSMS.DoesNotExist:
        raise ObjectDoesNotExist(f"Le fournisseur {fournisseur_id} n'existe pas.")

    # Interdire la suppression du provider par défaut s'il est unique/par défaut
    if getattr(provider, 'is_default', False):
        raise ValueError("Impossible de supprimer le fournisseur SMS configuré par défaut.")

    try:
        provider.delete()
        return {"action": "deleted"}
    except ProtectedError as e:
        if desactiver_si_protege:
            provider.is_active = False
            provider.save(update_fields=['is_active'])
            return {"action": "deactivated", "count": len(e.protected_objects)}
        
        raise ProviderSMSProtegeError(
            message=f"Impossible de supprimer ce fournisseur car {len(e.protected_objects)} envoi(s) SMS y sont rattachés.",
            count=len(e.protected_objects)
        )

""" 
def supprimer_fournisseur(fournisseur_id):
    ProviderSMS.objects.get(pk=fournisseur_id).delete() """


def _valider_payload_fournisseur(payload: dict):
    if not payload.get("nom"):
        raise ValidationError("Le nom du fournisseur est obligatoire.")
    if not payload.get("base_url"):
        raise ValidationError("L'URL de l'API est obligatoire.")
    if not payload.get("api_key"):
        raise ValidationError("La clé API est obligatoire.")
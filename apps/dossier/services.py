# services/dossier_service.py
"""
Couche service pour le module Dossier.
"""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

from client.models import Client
from client.services import nom_affichage   #Pouvoir
from dossier.models import Dossier

from apps.authentication.models import User
#from apps.authentication.models import Collaborateur
from django.db import transaction, IntegrityError


from django.utils import timezone
from facturation.models import Facture
from agenda.models import EvenementAgenda

#User = get_user_model()

# Champs de recherche libre : propres au dossier + nom du client lié (jointure)
CHAMPS_RECHERCHE_DOSSIER = ["reference", "intitule"]
CHAMPS_RECHERCHE_CLIENT = ["client__nom", "client__prenom", "client__raison_sociale"]

""" 
def dossier_vers_dict(dossier: Dossier) -> dict:
    return {
        "id": str(dossier.id),
        "reference": dossier.reference,
        "intitule": dossier.intitule,
        "type_affaire": dossier.type_affaire,
        "type_affaire_libelle": dossier.get_type_affaire_display(),
        "statut": dossier.statut,
        "statut_libelle": dossier.get_statut_display(),
        "client_id": str(dossier.client_id),
        "client_nom": nom_affichage(dossier.client),
        "avocat_referent_id": str(dossier.avocat_referent_id) if dossier.avocat_referent_id else None,
        "avocat_referent_nom": (
            dossier.avocat_referent.get_full_name() or dossier.avocat_referent.username
        ) if dossier.avocat_referent_id else None,
        #"juridiction": dossier.juridiction,
        "tribunal": {"id": str(dossier.tribunal.id), "code": dossier.tribunal.code, "nom": dossier.tribunal.nom} if dossier.tribunal else None,
        "date_ouverture": dossier.date_ouverture.isoformat() if dossier.date_ouverture else None,
        "date_prochaine_echeance": (
            dossier.date_prochaine_echeance.isoformat() if dossier.date_prochaine_echeance else None
        ),
        "description": dossier.description,
        "created_at": dossier.created_at.strftime("%d/%m/%Y %H:%M") if dossier.created_at else None,
    }
 """
def dossier_vers_dict(dossier: Dossier) -> dict:
    # Fonction locale utilitaire pour formater en ISO de manière sécurisée
    def format_date_iso(valeur_date):
        if not valeur_date:
            return None
        # Si c'est déjà une chaîne de caractères (str), on la renvoie telle quelle
        if isinstance(valeur_date, str):
            return valeur_date
        # Si c'est un vrai objet date/datetime Python, on appelle isoformat()
        return valeur_date.isoformat()

    return {
        "id": str(dossier.id),
        "reference": dossier.reference,
        "intitule": dossier.intitule,
        "type_affaire": dossier.type_affaire,
        "type_affaire_libelle": dossier.get_type_affaire_display(),
        "statut": dossier.statut,
        "statut_libelle": dossier.get_statut_display(),
        "client_id": str(dossier.client_id),
        "client_nom": nom_affichage(dossier.client),
        "avocat_referent_id": str(dossier.avocat_referent_id) if dossier.avocat_referent_id else None,
        "avocat_referent_nom": (
            dossier.avocat_referent.get_full_name() or dossier.avocat_referent.username
        ) if dossier.avocat_referent_id else None,
        "tribunal": {"id": str(dossier.tribunal.id), "code": dossier.tribunal.code, "nom": dossier.tribunal.nom} if dossier.tribunal else None,
        
        # UTILISATION DE LA METHODE SECURISÉE ICI 
        "date_ouverture": format_date_iso(dossier.date_ouverture),
        "date_prochaine_echeance": format_date_iso(dossier.date_prochaine_echeance),
        
        "description": dossier.description,
        "created_at": dossier.created_at.strftime("%d/%m/%Y %H:%M") if dossier.created_at else None,
    }

def lister_dossiers(
    recherche: str = "",
    statut: str = "",
    type_affaire: str = "",
    client_id: str = "",
    date_debut: str = "",
    date_fin: str = "",
    page: int = 1,
    page_size: int = 10,
    #tri: str = "-date_ouverture",
    tri: str = "-created_at", 
):
    """
    - recherche libre sur reference / intitule / juridiction / nom du client lié
    - filtres optionnels : statut, type_affaire, client_id
    - plage de dates optionnelle sur date_ouverture (date_debut / date_fin, YYYY-MM-DD)
    - pagination (page, page_size)
    """
    qs = Dossier.objects.select_related("client", "avocat_referent").all()

    if recherche:
        q_recherche = Q()
        for champ in CHAMPS_RECHERCHE_DOSSIER + CHAMPS_RECHERCHE_CLIENT:
            q_recherche |= Q(**{f"{champ}__icontains": recherche})
        qs = qs.filter(q_recherche)

    if statut:
        qs = qs.filter(statut=statut)
    if type_affaire:
        qs = qs.filter(type_affaire=type_affaire)
    if client_id:
        qs = qs.filter(client_id=client_id)

    if date_debut:
        qs = qs.filter(date_ouverture__gte=_parse_date(date_debut))
    if date_fin:
        qs = qs.filter(date_ouverture__lte=_parse_date(date_fin))

    qs = qs.order_by(tri).distinct()

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    return {
        "resultats": [dossier_vers_dict(d) for d in page_obj.object_list],
        "pagination": {
            "page_courante": page_obj.number,
            "nb_pages": paginator.num_pages,
            "nb_resultats": paginator.count,
            "page_size": page_size,
            "a_precedent": page_obj.has_previous(),
            "a_suivant": page_obj.has_next(),
        },
    }


def obtenir_dossier(dossier_id) -> Dossier:
    return Dossier.objects.select_related("client", "avocat_referent").get(pk=dossier_id)


def generer_numero_sequentiel_dossier() -> str:
    """
    Calcule le numéro séquentiel réel et disponible pour le dossier.
    Sécurisé contre les abandons de formulaires.
    """
    annee_actuelle = timezone.now().strftime("%Y") # Ex: "2026"
    prefixe = f"DOS-{annee_actuelle}-"
    
    # Recherche stricte du dernier numéro attribué en BDD pour cette année
    dernier_dossier = Dossier.objects.filter(
        reference__startswith=prefixe
    ).order_by('-reference').first()
    
    if dernier_dossier:
        try:
            # Récupère les 4 derniers chiffres (ex: "0042" -> 42)
            dernier_compteur = int(dernier_dossier.reference.split('-')[-1])
            nouveau_compteur = dernier_compteur + 1
        except (ValueError, IndexError):
            nouveau_compteur = 1
    else:
        nouveau_compteur = 1
        
    # Retourne le numéro final formaté sur 4 chiffres (ex: DOS-2026-0043)
    return f"{prefixe}{nouveau_compteur:04d}"

def creer_dossier(payload: dict, utilisateur) -> Dossier:
    _valider_payload(payload)
    print("dans creer_dossier --> ", payload, utilisateur)

    vraie_reference = generer_numero_sequentiel_dossier()

    for tentative in range(3):
        dossier = Dossier(
            reference=vraie_reference,
            intitule=payload["intitule"],
            type_affaire=payload.get("type_affaire", Dossier.TypeAffaire.AUTRE),
            statut=payload.get("statut", Dossier.StatutDossier.OUVERT),
            client_id=payload["client_id"],
            avocat_referent_id=payload.get("avocat_referent_id") or None,
            tribunal_id=payload.get("tribunal_id") or None,
            date_ouverture=payload.get("date_ouverture") or None,
            date_prochaine_echeance=payload.get("date_prochaine_echeance") or None,
            description=payload.get("description") or None,
            created_by=utilisateur,
        )
        print("le dossier avant full_clean() --> ", dossier)
        #dossier.full_clean(exclude=["reference"])  # référence générée automatiquement dans save()
        print("le dossier finale est --> ", dossier)
        try:
            with transaction.atomic():
                dossier.save()
            return dossier
        except IntegrityError:
            if tentative == 2:
                raise  # après 3 essais, on remonte l'erreur plutôt que de boucler indéfiniment
            continue  # une autre requête a pris la même référence entre-temps : on réessaie

def creer_facture_pour_dossier(dossier: Dossier, payload: dict, utilisateur) -> Facture:
    print("dans creer_facture_pour_dossier --> ",dossier, payload, utilisateur)

    annee_actuelle = timezone.now().strftime("%Y")
    prefixe = f"FAC-{annee_actuelle}-"

    for tentative in range(3):
        derniere_facture = Facture.objects.filter(numero__startswith=prefixe).order_by('-numero').first()
        nouveau_compteur = int(derniere_facture.numero.split('-')[-1]) + 1 if derniere_facture else 1
        numero_sequentiel = f"{prefixe}{nouveau_compteur:04d}"

        facture = Facture(
            client_id=dossier.client_id,
            dossier=dossier,
            numero=numero_sequentiel,
            montant_ht=payload.get('montant_ht') or 0,
            montant_ttc=payload.get('montant_ttc') or 0,
            taux_tva=payload.get('taux_tva') or 20.00,
            statut=payload.get('statut', 'brouillon'),
            date_emission=timezone.now().date(),
            date_echeance=payload.get('date_echeance') or None,
            description=payload.get('description') or None,
            created_by=utilisateur,
        )
        facture.full_clean(exclude=["numero"])
        print("la facture finale est --> ", facture)
        try:
            with transaction.atomic():
                facture.save()
            return facture
        except IntegrityError:
            if tentative == 2:
                raise
            continue


def creer_agenda_pour_dossier(dossier: Dossier, payload: dict, utilisateur) -> EvenementAgenda:
    print("dans creer_agenda_pour_dossier --> ",dossier, payload, utilisateur)
    agenda = EvenementAgenda(
        dossier=dossier,
        titre=payload['titre'],
        type=payload['type'],
        date_heure=payload.get('date_heure') or timezone.now(),
        critique=payload.get('critique', False),
        created_by=utilisateur,
    )
    agenda.full_clean()
    agenda.save()
    print("l'agenda finale est --> ", agenda)

    return agenda

""" def creer_dossier(payload: dict, utilisateur) -> Dossier:
    _valider_payload(payload)

    for tentative in range(3):
        dossier = Dossier(
            intitule=payload["intitule"],
            type_affaire=payload.get("type_affaire", Dossier.TypeAffaire.AUTRE),
            statut=payload.get("statut", Dossier.StatutDossier.OUVERT),
            client_id=payload["client_id"],
            avocat_referent_id=payload.get("avocat_referent_id") or None,
            tribunal_id=payload.get("tribunal_id") or None,
            date_ouverture=payload.get("date_ouverture") or None,
            date_prochaine_echeance=payload.get("date_prochaine_echeance") or None,
            description=payload.get("description") or None,
            created_by=utilisateur,
        )
        dossier.full_clean(exclude=["reference"])  # référence générée automatiquement dans save()
        try:
            with transaction.atomic():
                dossier.save()
            return dossier
        except IntegrityError:
            if tentative == 2:
                raise  # après 3 essais, on remonte l'erreur plutôt que de boucler indéfiniment
            continue  # une autre requête a pris la même référence entre-temps : on réessaie
 """



def modifier_dossier(dossier_id, payload: dict, utilisateur) -> Dossier:
    _valider_payload(payload)
    dossier = obtenir_dossier(dossier_id)
    dossier.reference = payload.get("reference", dossier.reference)
    dossier.intitule = payload.get("intitule", dossier.intitule)
    dossier.type_affaire = payload.get("type_affaire", dossier.type_affaire)
    dossier.statut = payload.get("statut", dossier.statut)
    dossier.client_id = payload.get("client_id", dossier.client_id)
    dossier.avocat_referent_id = payload.get("avocat_referent_id") or None
    #dossier.juridiction = payload.get("juridiction") or None
    dossier.tribunal_id=payload.get("tribunal_id", dossier.tribunal_id) or None
    dossier.date_ouverture = payload.get("date_ouverture") or None
    dossier.date_prochaine_echeance = payload.get("date_prochaine_echeance") or None
    dossier.description = payload.get("description") or None
    dossier.edited_by = utilisateur
    dossier.full_clean()
    dossier.save()
    return dossier


def supprimer_dossier(dossier_id):
    dossier = obtenir_dossier(dossier_id)
    dossier.delete()


def options_clients():
    """Alimente le <select> client du modal Dossier (création/édition)."""
    return [
        {"id": str(c.id), "nom": nom_affichage(c)}
        for c in Client.objects.all().order_by("nom", "raison_sociale")
    ]


def options_avocats():
    """Alimente le <select> avocat référent du modal Dossier."""
    return [
        {"id": str(u.id), "nom": u.get_full_name() or u.username}
        #for u in User.objects.filter(role__in=["associe", "avocat"]).order_by("prenom")
        for u in User.objects.filter(role__in=["associe", "avocat"]).order_by("first_name")

    ]


def _valider_payload(payload: dict):
    if not payload.get("reference"):
        raise ValidationError("La référence du dossier est obligatoire.")
    if not payload.get("intitule"):
        raise ValidationError("L'intitulé du dossier est obligatoire.")
    if not payload.get("client_id"):
        raise ValidationError("Le client rattaché au dossier est obligatoire.")


def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()
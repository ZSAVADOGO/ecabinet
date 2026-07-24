# services/dossier_service.py
"""
Couche service pour le module Dossier.
"""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q

from client.models import Client
from client.services import nom_affichage   #Pouvoir
from dossier.models import Dossier

from datetime import date

from apps.authentication.models import User
#from apps.authentication.models import Collaborateur
from django.db import transaction, IntegrityError
#from apps.authentication.models import PartiePrenante  # adapte le chemin d'import si le modèle vit ailleurs


from apps.authentication.models import Chambre


from django.utils import timezone
from facturation.models import Facture
from agenda.models import EvenementAgenda, PartiePrenante

#User = get_user_model()

# Champs de recherche libre : propres au dossier + nom du client lié (jointure)
CHAMPS_RECHERCHE_DOSSIER = ["reference", "intitule"]
CHAMPS_RECHERCHE_CLIENT = ["client__nom", "client__prenom", "client__raison_sociale"]

def dossier_vers_dict(dossier: Dossier) -> dict:
    def format_date_iso(valeur):
        if not valeur:
            return None
        return valeur if isinstance(valeur, str) else valeur.isoformat()

    return {
        "id": str(dossier.id),
        "reference": dossier.reference,
        "numero_role": dossier.numero_role,
        "intitule": dossier.intitule,
        "type_affaire": dossier.type_affaire,
        "type_affaire_libelle": dossier.get_type_affaire_display(),
        "statut": dossier.statut,
        "statut_libelle": dossier.get_statut_display(),
        "degre_instance": dossier.degre_instance,
        "degre_instance_libelle": dossier.get_degre_instance_display(),
        "client_id": str(dossier.client_id),
        "client_nom": nom_affichage(dossier.client),
        "partie_adverse": dossier.partie_adverse,
        "avocat_adverse": dossier.avocat_adverse,
        "avocat_referent_id": str(dossier.avocat_referent_id) if dossier.avocat_referent_id else None,
        "avocat_referent_nom": (dossier.avocat_referent.get_full_name() or dossier.avocat_referent.username) if dossier.avocat_referent_id else None,
        "tribunal": {"id": str(dossier.tribunal.id), "code": dossier.tribunal.code, "nom": dossier.tribunal.nom} if dossier.tribunal_id else None,
        "chambre": {"id": str(dossier.chambre.id), "libelle": dossier.chambre.libelle} if dossier.chambre_id else None,
        "juge_en_charge": dossier.juge_en_charge,
        "numero_bureau": dossier.numero_bureau,
        "date_ouverture": format_date_iso(dossier.date_ouverture),
        "date_prochaine_echeance": format_date_iso(dossier.date_prochaine_echeance),
        "description": dossier.description,
        "created_at": dossier.created_at.strftime("%d/%m/%Y %H:%M") if dossier.created_at else None,
        "echeance_depassee": bool(
            dossier.date_prochaine_echeance
            and dossier.date_prochaine_echeance < date.today()
            and dossier.statut not in ('clos', 'archive')
        ),
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
    vraie_reference = generer_numero_sequentiel_dossier()

    for tentative in range(3):
        dossier = Dossier(
            reference=vraie_reference,
            numero_role=payload.get("numero_role") or None,
            intitule=payload["intitule"],
            type_affaire=payload.get("type_affaire", Dossier.TypeAffaire.AUTRE),
            statut=payload.get("statut", Dossier.StatutDossier.OUVERT),
            degre_instance=payload.get("degre_instance", Dossier.DegreInstance.PREMIERE_INSTANCE),
            dossier_origine_id=payload.get("dossier_origine_id") or None,
            client_id=payload["client_id"],
            partie_adverse=payload.get("partie_adverse") or None,
            avocat_adverse=payload.get("avocat_adverse") or None,
            avocat_referent_id=payload.get("avocat_referent_id") or None,
            tribunal_id=payload.get("tribunal_id") or None,
            chambre_id=payload.get("chambre_id") or None,
            juge_en_charge=payload.get("juge_en_charge") or None,
            numero_bureau=payload.get("numero_bureau") or None,
            date_ouverture=payload.get("date_ouverture") or None,
            date_prochaine_echeance=payload.get("date_prochaine_echeance") or None,
            description=payload.get("description") or None,
            created_by=utilisateur,
        )
        dossier.full_clean(exclude=["reference"])  # <- réactivée, ne plus jamais commenter cette ligne
        try:
            with transaction.atomic():
                dossier.save()
            return dossier
        except IntegrityError:
            if tentative == 2:
                raise
            vraie_reference = generer_numero_sequentiel_dossier()  # recalcul avant le prochain essai
            continue


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


def modifier_dossier(dossier_id, payload: dict, utilisateur) -> Dossier:
    print("le payload dans le service --> ", payload)
    # 1. Extraction des données du sous-dictionnaire "dossier" s'il existe
    data = payload.get("dossier", payload)
    print("le reference extrait --> ", data.get("reference"))
    # Valider les données extraites
    _valider_payload(data)
    # Récupération de l'instance
    dossier = obtenir_dossier(dossier_id)
    # 2. Mise à jour des champs depuis `data` (sans la virgule à la fin)
    dossier.reference = data.get("reference", dossier.reference)  
    dossier.numero_role = data.get("numero_role") or None
    dossier.intitule = data.get("intitule", dossier.intitule)
    dossier.type_affaire = data.get("type_affaire", dossier.type_affaire)
    dossier.statut = data.get("statut", dossier.statut)
    dossier.degre_instance = data.get("degre_instance", dossier.degre_instance)
    dossier.dossier_origine_id = data.get("dossier_origine_id") or None
    dossier.client_id = data.get("client_id", dossier.client_id)
    dossier.partie_adverse = data.get("partie_adverse") or None
    dossier.avocat_adverse = data.get("avocat_adverse") or None
    dossier.avocat_referent_id = data.get("avocat_referent_id") or None
    dossier.tribunal_id = data.get("tribunal_id") or None
    dossier.chambre_id = data.get("chambre_id") or None
    dossier.juge_en_charge = data.get("juge_en_charge") or None
    dossier.numero_bureau = data.get("numero_bureau") or None
    dossier.date_ouverture = data.get("date_ouverture") or None
    dossier.date_prochaine_echeance = data.get("date_prochaine_echeance") or None
    dossier.description = data.get("description") or None
    
    dossier.edited_by = utilisateur
    
    # Validation des contraintes du modèle Django
    dossier.full_clean()
    dossier.save()
    
    return dossier



def supprimer_dossier(dossier_id):
  
    try:
        # On cible directement l'objet via un .get() minimaliste, suffisant pour .delete()
        dossier = Dossier.objects.get(pk=dossier_id)
    except Dossier.DoesNotExist:
        raise ObjectDoesNotExist("Dossier introuvable.")
        
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

def options_chambres(tribunal_id=None):
    """Alimente le <select> Chambre, filtré par tribunal si fourni."""
    qs = Chambre.objects.select_related("tribunal").all()
    if tribunal_id:
        qs = qs.filter(tribunal_id=tribunal_id)
    return [{"id": str(c.id), "libelle": c.libelle, "tribunal_id": str(c.tribunal_id)} for c in qs]

def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()


def creer_parties_prenantes_pour_dossier(dossier: Dossier, liste_parties: list, utilisateur) -> list[PartiePrenante]:
    """
    Crée en masse les parties prenantes rattachées à un dossier.
    liste_parties : [{nom, role, telephone, email, notifiable}, ...]
    """
    parties_creees = []
    for item in liste_parties:
        if not item.get("nom"):
            continue  # ligne vide envoyée par erreur depuis le wizard : on l'ignore silencieusement
        partie = PartiePrenante(
            dossier=dossier,
            nom=item["nom"],
            role=item.get("role", PartiePrenante.RolePartiePrenante.AUTRE if hasattr(PartiePrenante, 'RolePartiePrenante') else "autre"),
            telephone=item.get("telephone") or None,
            email=item.get("email") or None,
            notifiable=bool(item.get("notifiable", True)),
            created_by=utilisateur,
        )
        partie.full_clean()
        partie.save()
        parties_creees.append(partie)
    return parties_creees
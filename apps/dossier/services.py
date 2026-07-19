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

#User = get_user_model()

# Champs de recherche libre : propres au dossier + nom du client lié (jointure)
CHAMPS_RECHERCHE_DOSSIER = ["reference", "intitule", "juridiction"]
CHAMPS_RECHERCHE_CLIENT = ["client__nom", "client__prenom", "client__raison_sociale"]


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
        "juridiction": dossier.juridiction,
        "date_ouverture": dossier.date_ouverture.isoformat() if dossier.date_ouverture else None,
        "date_prochaine_echeance": (
            dossier.date_prochaine_echeance.isoformat() if dossier.date_prochaine_echeance else None
        ),
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
    tri: str = "-date_ouverture",
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


def creer_dossier(payload: dict, utilisateur) -> Dossier:
    _valider_payload(payload)
    dossier = Dossier(
        reference=payload["reference"],
        intitule=payload["intitule"],
        type_affaire=payload.get("type_affaire", Dossier.TypeAffaire.AUTRE),
        statut=payload.get("statut", Dossier.StatutDossier.OUVERT),
        client_id=payload["client_id"],
        avocat_referent_id=payload.get("avocat_referent_id") or None,
        juridiction=payload.get("juridiction") or None,
        date_ouverture=payload.get("date_ouverture") or None,
        date_prochaine_echeance=payload.get("date_prochaine_echeance") or None,
        description=payload.get("description") or None,
        created_by=utilisateur,
    )
    dossier.full_clean()
    dossier.save()
    return dossier


def modifier_dossier(dossier_id, payload: dict, utilisateur) -> Dossier:
    _valider_payload(payload)
    dossier = obtenir_dossier(dossier_id)
    dossier.reference = payload.get("reference", dossier.reference)
    dossier.intitule = payload.get("intitule", dossier.intitule)
    dossier.type_affaire = payload.get("type_affaire", dossier.type_affaire)
    dossier.statut = payload.get("statut", dossier.statut)
    dossier.client_id = payload.get("client_id", dossier.client_id)
    dossier.avocat_referent_id = payload.get("avocat_referent_id") or None
    dossier.juridiction = payload.get("juridiction") or None
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
        for u in User.objects.filter(role__in=["associe", "avocat"]).order_by("prenom")
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
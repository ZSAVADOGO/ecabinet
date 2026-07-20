# services/client_service.py
"""
Couche service pour le module Client.
Toute la logique métier (recherche, pagination, validation, CRUD) est isolée
ici pour rester indépendante des vues (contrôleurs) et testable unitairement.
"""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models import Q
from django.db.models.deletion import RestrictedError

from client.models import Client

# Champs sur lesquels porte la recherche libre (3-4 champs, cf. cahier des charges)
CHAMPS_RECHERCHE = ["nom", "prenom", "raison_sociale", "telephone1", "email"]


def nom_affichage(client: Client) -> str:
    """Calcule un nom d'affichage unique, quel que soit le type de client."""
    if client.type == Client.ClientType.PERSONNE_MORALE:
        return client.raison_sociale or "(Raison sociale non renseignée)"
    return f"{client.prenom or ''} {client.nom or ''}".strip() or "(Nom non renseigné)"


def client_vers_dict(client: Client) -> dict:
    return {
        "id": str(client.id),
        "type": client.type,
        "type_libelle": client.get_type_display(),
        "nom": client.nom,
        "prenom": client.prenom,
        "raison_sociale": client.raison_sociale,
        "nom_affichage": nom_affichage(client),
        "ifu_rccm": client.ifu_rccm,
        "email": client.email,
        "telephone1": client.telephone1,
        "telephone2": client.telephone2,
        "adresse": client.adresse,
        "notes": client.notes, 
        "nb_dossiers": client.nb_dossiers if hasattr(client, 'nb_dossiers') else client.dossiers.count(),
        "created_at": client.created_at.strftime("%d/%m/%Y %H:%M") if client.created_at else None,
    }


def lister_clients(
    recherche: str = "",
    type_client: str = "",
    date_debut: str = "",
    date_fin: str = "",
    page: int = 1,
    page_size: int = 10,
    tri: str = "-created_at",
):
    """
    Retourne un dict prêt à être sérialisé en JSON pour le tableau du dashboard :
    - recherche libre sur nom / prenom / raison_sociale / telephone1 / email
    - filtre optionnel par type de client
    - filtre optionnel par plage de dates de création (date_debut / date_fin, format YYYY-MM-DD)
    - pagination (page, page_size)
    """
    qs = Client.objects.annotate(nb_dossiers=Count("dossiers"))

    if recherche:
        q_recherche = Q()
        for champ in CHAMPS_RECHERCHE:
            q_recherche |= Q(**{f"{champ}__icontains": recherche})
        qs = qs.filter(q_recherche)

    if type_client:
        qs = qs.filter(type=type_client)

    if date_debut:
        qs = qs.filter(created_at__date__gte=_parse_date(date_debut))
    if date_fin:
        qs = qs.filter(created_at__date__lte=_parse_date(date_fin))

    qs = qs.order_by(tri)

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    return {
        "resultats": [client_vers_dict(c) for c in page_obj.object_list],
        "pagination": {
            "page_courante": page_obj.number,
            "nb_pages": paginator.num_pages,
            "nb_resultats": paginator.count,
            "page_size": page_size,
            "a_precedent": page_obj.has_previous(),
            "a_suivant": page_obj.has_next(),
        },
    }


def obtenir_client(client_id) -> Client:
    return Client.objects.get(pk=client_id)


def creer_client(payload: dict, utilisateur) -> Client:
    _valider_payload(payload)
    client = Client(
        type=payload.get("type", Client.ClientType.PERSONNE_PHYSIQUE),
        nom=payload.get("nom") or None,
        prenom=payload.get("prenom") or None,
        raison_sociale=payload.get("raison_sociale") or None,
        ifu_rccm=payload.get("ifu_rccm") or None,
        email=payload.get("email") or None,
        telephone1=payload.get("telephone1"),
        telephone2=payload.get("telephone2") or None,
        adresse=payload.get("adresse") or None,
        notes=payload.get("notes") or None,
        created_by=utilisateur,
    )
    client.full_clean()
    client.save()
    return client


def modifier_client(client_id, payload: dict, utilisateur) -> Client:
    _valider_payload(payload)
    client = obtenir_client(client_id)
    client.type = payload.get("type", client.type)
    client.nom = payload.get("nom") or None
    client.prenom = payload.get("prenom") or None
    client.raison_sociale = payload.get("raison_sociale") or None
    client.ifu_rccm = payload.get("ifu_rccm") or None
    client.email = payload.get("email") or None
    client.telephone1 = payload.get("telephone1", client.telephone1)
    client.telephone2 = payload.get("telephone2") or None
    client.adresse = payload.get("adresse") or None
    client.notes = payload.get("notes") or None
    client.edited_by = utilisateur
    client.full_clean()
    client.save()
    return client


def supprimer_client(client_id):
    """
    Supprime un client. Le FK Dossier -> Client est en RESTRICT : si le client
    a des dossiers rattachés, Django lève RestrictedError. On remonte un message
    métier clair plutôt que de laisser fuiter l'exception technique.
    """
    client = obtenir_client(client_id)
    try:
        client.delete()
    except RestrictedError:
        raise ValidationError(
            "Impossible de supprimer ce client : il possède au moins un dossier "
            "rattaché. Archivez ou réaffectez ses dossiers avant suppression."
        )


def _valider_payload(payload: dict):
    type_client = payload.get("type")
    if type_client == Client.ClientType.PERSONNE_MORALE and not payload.get("raison_sociale"):
        raise ValidationError("La raison sociale est obligatoire pour une personne morale.")
    if type_client == Client.ClientType.PERSONNE_PHYSIQUE and not payload.get("nom"):
        raise ValidationError("Le nom est obligatoire pour une personne physique.")
    if not payload.get("telephone1"):
        raise ValidationError("Le téléphone principal est obligatoire.")


def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()
# facturation/services/facturation_service.py
"""
Couche service du module Facturation.
Modèle de référence : Facture (table `factures`)
    id, numero, client (FK), dossier (FK nullable), montant_ht, taux_tva,
    statut (brouillon|envoyee|payee|en_retard), date_emission, date_echeance,
    created_by, edited_by, created_at, updated_at.
"""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

from client.models import Client

from client.services import nom_affichage   #Pouvoir
#from client.services.client_service import nom_affichage
#from client.services import obtenir_client, lister_clients, creer_client, modifier_client, supprimer_client, client_vers_dict

from dossier.models import Dossier
from facturation.models import Facture

CHAMPS_RECHERCHE = ["numero", "client__nom", "client__prenom", "client__raison_sociale", "dossier__reference"]


def facture_vers_dict(facture: Facture) -> dict:
    montant_ttc = round(float(facture.montant_ht) * (1 + float(facture.taux_tva) / 100), 2)
    return {
        "id": str(facture.id),
        "numero": facture.numero,
        "client_id": str(facture.client_id),
        "client_nom": nom_affichage(facture.client),
        "dossier_id": str(facture.dossier_id) if facture.dossier_id else None,
        "dossier_reference": facture.dossier.reference if facture.dossier_id else None,
        "montant_ht": float(facture.montant_ht),
        "taux_tva": float(facture.taux_tva),
        "montant_ttc": montant_ttc,
        "statut": facture.statut,
        "statut_libelle": facture.get_statut_display(),
        "date_emission": facture.date_emission.isoformat() if facture.date_emission else None,
        "date_echeance": facture.date_echeance.isoformat() if facture.date_echeance else None,
        "created_at": facture.created_at.strftime("%d/%m/%Y %H:%M") if facture.created_at else None,
    }


def _queryset_filtre(recherche="", statut="", client_id="", date_debut="", date_fin=""):
    qs = Facture.objects.select_related("client", "dossier").all()

    if recherche:
        q_recherche = Q()
        for champ in CHAMPS_RECHERCHE:
            q_recherche |= Q(**{f"{champ}__icontains": recherche})
        qs = qs.filter(q_recherche)

    if statut:
        qs = qs.filter(statut=statut)
    if client_id:
        qs = qs.filter(client_id=client_id)

    if date_debut:
        qs = qs.filter(date_emission__gte=_parse_date(date_debut))
    if date_fin:
        qs = qs.filter(date_emission__lte=_parse_date(date_fin))

    return qs.distinct()


def lister_factures(recherche="", statut="", client_id="", date_debut="", date_fin="",
                     page=1, page_size=10, tri="-date_emission"):
    qs = _queryset_filtre(recherche, statut, client_id, date_debut, date_fin).order_by(tri)
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    return {
        "resultats": [facture_vers_dict(f) for f in page_obj.object_list],
        "pagination": {
            "page_courante": page_obj.number,
            "nb_pages": paginator.num_pages,
            "nb_resultats": paginator.count,
            "page_size": page_size,
            "a_precedent": page_obj.has_previous(),
            "a_suivant": page_obj.has_next(),
        },
    }


def obtenir_facture(facture_id) -> Facture:
    return Facture.objects.select_related("client", "dossier").get(pk=facture_id)


def _generer_numero() -> str:
    annee = datetime.now().year
    dernier = Facture.objects.filter(numero__startswith=f"FACT-{annee}-").order_by("-numero").first()
    prochain = int(dernier.numero.split("-")[-1]) + 1 if dernier else 1
    return f"FACT-{annee}-{prochain:04d}"


def creer_facture(payload: dict, utilisateur) -> Facture:
    _valider_payload(payload)
    facture = Facture(
        numero=payload.get("numero") or _generer_numero(),
        client_id=payload["client_id"],
        dossier_id=payload.get("dossier_id") or None,
        montant_ht=payload["montant_ht"],
        taux_tva=payload.get("taux_tva", 18.00),
        statut=payload.get("statut", "brouillon"),
        date_emission=payload["date_emission"],
        date_echeance=payload.get("date_echeance") or None,
        created_by=utilisateur,
    )
    facture.full_clean()
    facture.save()
    return facture


def modifier_facture(facture_id, payload: dict, utilisateur) -> Facture:
    _valider_payload(payload)
    facture = obtenir_facture(facture_id)
    facture.numero = payload.get("numero", facture.numero)
    facture.client_id = payload.get("client_id", facture.client_id)
    facture.dossier_id = payload.get("dossier_id") or None
    facture.montant_ht = payload.get("montant_ht", facture.montant_ht)
    facture.taux_tva = payload.get("taux_tva", facture.taux_tva)
    facture.statut = payload.get("statut", facture.statut)
    facture.date_emission = payload.get("date_emission", facture.date_emission)
    facture.date_echeance = payload.get("date_echeance") or None
    facture.edited_by = utilisateur
    facture.full_clean()
    facture.save()
    return facture


def supprimer_facture(facture_id):
    obtenir_facture(facture_id).delete()


def options_clients():
    return [{"id": str(c.id), "nom": nom_affichage(c)} for c in Client.objects.all().order_by("nom", "raison_sociale")]


def options_dossiers():
    return [
        {"id": str(d.id), "label": f"{d.reference} — {d.intitule}", "client_id": str(d.client_id)}
        for d in Dossier.objects.all().order_by("-date_ouverture")[:500]
    ]


def _valider_payload(payload: dict):
    if not payload.get("client_id"):
        raise ValidationError("Le client est obligatoire.")
    if not payload.get("montant_ht"):
        raise ValidationError("Le montant HT est obligatoire.")
    if not payload.get("date_emission"):
        raise ValidationError("La date d'émission est obligatoire.")


def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()
# agenda/services/agenda_service.py
"""
Couche service du module Agenda.
Modèle de référence : EvenementAgenda (table `evenements_agenda`)
    id, titre, type (audience|rdv_client|delai_procedure|autre), date_heure,
    critique (bool), dossier (FK Dossier, nullable), created_by, edited_by,
    created_at, updated_at.
"""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

from agenda.models import EvenementAgenda
from dossier.models import Dossier

CHAMPS_RECHERCHE = ["titre", "dossier__reference", "dossier__intitule"]


def evenement_vers_dict(evt: EvenementAgenda) -> dict:
    return {
        "id": str(evt.id),
        "titre": evt.titre,
        "type": evt.type,
        "type_libelle": evt.get_type_display(),
        "date_heure": evt.date_heure.isoformat() if evt.date_heure else None,
        "critique": evt.critique,
        "dossier_id": str(evt.dossier_id) if evt.dossier_id else None,
        "dossier_reference": evt.dossier.reference if evt.dossier_id else None,
        "dossier_intitule": evt.dossier.intitule if evt.dossier_id else None,
        "created_at": evt.created_at.strftime("%d/%m/%Y %H:%M") if evt.created_at else None,
    }


def _queryset_filtre(recherche="", type_evenement="", dossier_id="", critique="", date_debut="", date_fin=""):
    qs = EvenementAgenda.objects.select_related("dossier").all()

    if recherche:
        q_recherche = Q()
        for champ in CHAMPS_RECHERCHE:
            q_recherche |= Q(**{f"{champ}__icontains": recherche})
        qs = qs.filter(q_recherche)

    if type_evenement:
        qs = qs.filter(type=type_evenement)
    if dossier_id:
        qs = qs.filter(dossier_id=dossier_id)
    if critique in ("true", "1"):
        qs = qs.filter(critique=True)

    if date_debut:
        qs = qs.filter(date_heure__date__gte=_parse_date(date_debut))
    if date_fin:
        qs = qs.filter(date_heure__date__lte=_parse_date(date_fin))

    return qs.distinct()


def lister_evenements(
    recherche="", type_evenement="", dossier_id="", critique="",
    date_debut="", date_fin="", page=1, page_size=10, tri="date_heure",
):
    qs = _queryset_filtre(recherche, type_evenement, dossier_id, critique, date_debut, date_fin).order_by(tri)
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    return {
        "resultats": [evenement_vers_dict(e) for e in page_obj.object_list],
        "pagination": {
            "page_courante": page_obj.number,
            "nb_pages": paginator.num_pages,
            "nb_resultats": paginator.count,
            "page_size": page_size,
            "a_precedent": page_obj.has_previous(),
            "a_suivant": page_obj.has_next(),
        },
    }


def obtenir_evenement(evenement_id) -> EvenementAgenda:
    return EvenementAgenda.objects.select_related("dossier").get(pk=evenement_id)


def creer_evenement(payload: dict, utilisateur) -> EvenementAgenda:
    _valider_payload(payload)
    evt = EvenementAgenda(
        titre=payload["titre"],
        type=payload.get("type", "autre"),
        date_heure=payload["date_heure"],
        critique=str(payload.get("critique", False)) in ("true", "1", "True"),
        dossier_id=payload.get("dossier_id") or None,
        created_by=utilisateur,
    )
    evt.full_clean()
    evt.save()
    return evt


def modifier_evenement(evenement_id, payload: dict, utilisateur) -> EvenementAgenda:
    _valider_payload(payload)
    evt = obtenir_evenement(evenement_id)
    evt.titre = payload.get("titre", evt.titre)
    evt.type = payload.get("type", evt.type)
    evt.date_heure = payload.get("date_heure", evt.date_heure)
    evt.critique = str(payload.get("critique", evt.critique)) in ("true", "1", "True")
    evt.dossier_id = payload.get("dossier_id") or None
    evt.edited_by = utilisateur
    evt.full_clean()
    evt.save()
    return evt


def supprimer_evenement(evenement_id):
    obtenir_evenement(evenement_id).delete()


def options_dossiers():
    return [
        {"id": str(d.id), "label": f"{d.reference} — {d.intitule}"}
        for d in Dossier.objects.all().order_by("-date_ouverture")[:500]
    ]



def _valider_payload(payload: dict):
    if not payload.get("titre"):
        raise ValidationError("Le titre de l'événement est obligatoire.")
    if not payload.get("date_heure"):
        raise ValidationError("La date/heure de l'événement est obligatoire.")


def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()
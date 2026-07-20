# facturation/services/finance_service.py
"""
Couche service du module Finance (reporting).
Contrairement à `facturation` (CRUD des factures), ce module est en LECTURE
SEULE : il agrège les données de Facture pour produire un tableau de bord
(chiffre d'affaires, encaissé, en attente, en retard, répartition mensuelle,
top clients) sur une plage de dates donnée.
"""

from datetime import datetime

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from client.models import Client
from client.services import nom_affichage
from facturation.models import Facture


def _queryset_periode(date_debut="", date_fin="", client_id=""):
    qs = Facture.objects.select_related("client").all()
    if date_debut:
        qs = qs.filter(date_emission__gte=_parse_date(date_debut))
    if date_fin:
        qs = qs.filter(date_emission__lte=_parse_date(date_fin))
    if client_id:
        qs = qs.filter(client_id=client_id)
    return qs


def obtenir_tableau_bord(date_debut="", date_fin="", client_id=""):
    qs = _queryset_periode(date_debut, date_fin, client_id)

    total_ht = qs.aggregate(total=Sum("montant_ht"))["total"] or 0
    encaisse_ht = qs.filter(statut="payee").aggregate(total=Sum("montant_ht"))["total"] or 0
    en_attente_ht = qs.filter(statut__in=["brouillon", "envoyee"]).aggregate(total=Sum("montant_ht"))["total"] or 0
    en_retard_ht = qs.filter(statut="en_retard").aggregate(total=Sum("montant_ht"))["total"] or 0
    nb_factures = qs.count()

    repartition_mensuelle = list(
        qs.annotate(mois=TruncMonth("date_emission"))
        .values("mois")
        .annotate(total_ht=Sum("montant_ht"), nb=Count("id"))
        .order_by("mois")
    )
    repartition_mensuelle = [
        {
            "mois": r["mois"].strftime("%Y-%m") if r["mois"] else None,
            "mois_libelle": r["mois"].strftime("%b %Y") if r["mois"] else None,
            "total_ht": float(r["total_ht"] or 0),
            "nb_factures": r["nb"],
        }
        for r in repartition_mensuelle
    ]

    top_clients_qs = (
        qs.values("client_id")
        .annotate(total_ht=Sum("montant_ht"), nb=Count("id"))
        .order_by("-total_ht")[:10]
    )
    top_clients = []
    # Optimisation N+1 : On récupère tous les clients nécessaires en une seule requête
    client_ids = [ligne["client_id"] for ligne in top_clients_qs]
    clients_par_id = {str(c.id): c for c in Client.objects.filter(id__in=client_ids)}

    for ligne in top_clients_qs:
        client = clients_par_id.get(str(ligne["client_id"]))
        top_clients.append({
            "client_id": str(ligne["client_id"]),
            "client_nom": nom_affichage(client) if client else "Client Inconnu",
            "total_ht": float(ligne["total_ht"] or 0),
            "nb_factures": ligne["nb"],
        })

    max_mensuel = max((m["total_ht"] for m in repartition_mensuelle), default=0)
    for m in repartition_mensuelle:
        m["pourcentage_barre"] = round((m["total_ht"] / max_mensuel) * 100, 1) if max_mensuel else 0

    return {
        "kpis": {
            "total_ht": float(total_ht),
            "encaisse_ht": float(encaisse_ht),
            "en_attente_ht": float(en_attente_ht),
            "en_retard_ht": float(en_retard_ht),
            "nb_factures": nb_factures,
        },
        "repartition_mensuelle": repartition_mensuelle,
        "top_clients": top_clients,
    }


def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()
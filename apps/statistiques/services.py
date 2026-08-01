from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.utils import timezone

from dossier.models import Dossier
from client.models import Client
from agenda.models import EvenementAgenda
from facturation.models import Facture
from notifications.models import SMSDetailDestinataire, SMSGroupEnvoi
from datetime import datetime, timedelta


def _plage_dates(date_debut_str, date_fin_str):
    debut = datetime.strptime(date_debut_str, "%Y-%m-%d").date() if date_debut_str else None
    fin = datetime.strptime(date_fin_str, "%Y-%m-%d").date() if date_fin_str else None
    return debut, fin

def kpis_juridiques(date_debut=None, date_fin=None):
    aujourdhui = timezone.now().date()
    debut, fin = _plage_dates(date_debut, date_fin)

    # ---- "Période" : suit le filtre, "Toutes les dates" = depuis toujours ----
    qs_periode = Dossier.objects.all()
    if debut:
        qs_periode = qs_periode.filter(date_ouverture__gte=debut)
    if fin:
        qs_periode = qs_periode.filter(date_ouverture__lte=fin)

    total_dossiers_periode = qs_periode.count()

    libelles_type = dict(Dossier.TypeAffaire.choices)
    repartition_type = [
        {"libelle": libelles_type.get(r['type_affaire'], r['type_affaire']), "total": r['total']}
        for r in qs_periode.values('type_affaire').annotate(total=Count('id')).order_by('-total')
    ]
    max_type = max((r['total'] for r in repartition_type), default=1)
    for r in repartition_type:
        r['pourcentage'] = round((r['total'] / max_type) * 100)

    top_clients = [
        {"nom": r['client__nom'] or r['client__raison_sociale'] or 'Client', "total": r['total']}
        for r in qs_periode.values('client__nom', 'client__raison_sociale')
                 .annotate(total=Count('id')).order_by('-total')[:5]
    ]
    max_client = max((c['total'] for c in top_clients), default=1)
    for c in top_clients:
        c['pourcentage'] = round((c['total'] / max_client) * 100)

    # ---- "Temps réel" : jamais affecté par le filtre (état présent, pas historique) ----
    dossiers_actifs = Dossier.objects.exclude(statut__in=['clos', 'archive']).count()
    echeances_a_risque = (
        Dossier.objects.exclude(statut__in=['clos', 'archive'])
        .filter(date_prochaine_echeance__gte=aujourdhui, date_prochaine_echeance__lte=aujourdhui + timedelta(days=7))
        .count()
    )
    echeances_depassees = (
        Dossier.objects.exclude(statut__in=['clos', 'archive'])
        .filter(date_prochaine_echeance__lt=aujourdhui)
        .count()
    )

    return {
        "total_dossiers_periode": total_dossiers_periode,
        "dossiers_actifs": dossiers_actifs,
        "echeances_a_risque": echeances_a_risque,
        "echeances_depassees": echeances_depassees,
        "repartition_type": repartition_type,
        "top_clients": top_clients,
    }


def kpis_secretariat(date_debut=None, date_fin=None):
    aujourdhui = timezone.now().date()
    debut, fin = _plage_dates(date_debut, date_fin)

    qs_clients = Client.objects.all()
    qs_evenements = EvenementAgenda.objects.all()
    qs_sms = SMSDetailDestinataire.objects.all()
    if debut:
        qs_clients = qs_clients.filter(created_at__date__gte=debut)
        qs_evenements = qs_evenements.filter(date_heure__date__gte=debut)
        qs_sms = qs_sms.filter(group_envoi__created_at__date__gte=debut)
    if fin:
        qs_clients = qs_clients.filter(created_at__date__lte=fin)
        qs_evenements = qs_evenements.filter(date_heure__date__lte=fin)
        qs_sms = qs_sms.filter(group_envoi__created_at__date__lte=fin)

    nouveaux_clients_periode = qs_clients.count()
    evenements_periode = qs_evenements.count()

    sms_stats = qs_sms.aggregate(total=Count('id'), livres=Count('id', filter=Q(status='DELIVERY_SUCCESS')))
    taux_livraison = round((sms_stats['livres'] / sms_stats['total'] * 100), 1) if sms_stats['total'] else 0

    # Temps réel : événements critiques réellement à venir dès maintenant
    evenements_critiques_a_venir = EvenementAgenda.objects.filter(critique=True, date_heure__date__gte=aujourdhui).count()

    return {
        "nouveaux_clients_periode": nouveaux_clients_periode,
        "evenements_periode": evenements_periode,
        "evenements_critiques_a_venir": evenements_critiques_a_venir,
        "sms_total": sms_stats['total'],
        "sms_taux_livraison": taux_livraison,
    }


def kpis_comptable(date_debut=None, date_fin=None):
    debut, fin = _plage_dates(date_debut, date_fin)

    qs_factures = Facture.objects.all()
    qs_sms_groupes = SMSGroupEnvoi.objects.all()
    if debut:
        qs_factures = qs_factures.filter(date_emission__gte=debut)
        qs_sms_groupes = qs_sms_groupes.filter(created_at__date__gte=debut)
    if fin:
        qs_factures = qs_factures.filter(date_emission__lte=fin)
        qs_sms_groupes = qs_sms_groupes.filter(created_at__date__lte=fin)

    ca_periode = qs_factures.filter(statut='payee').aggregate(t=Sum('montant_ttc'))['t'] or 0
    cout_sms_periode = qs_sms_groupes.aggregate(t=Sum('cost'))['t'] or 0

    libelles_statut = dict(Facture.StatutFacture.choices) if hasattr(Facture, 'StatutFacture') else {}
    repartition_statut = [
        {"libelle": libelles_statut.get(r['statut'], r['statut']), "total": r['total'], "montant": r['montant'] or 0}
        for r in qs_factures.values('statut').annotate(total=Count('id'), montant=Sum('montant_ttc')).order_by('-montant')
    ]

    # Temps réel : impayé/retard reflètent l'état ACTUEL des factures, pas une période passée révolue
    montant_impaye = Facture.objects.exclude(statut='payee').aggregate(t=Sum('montant_ttc'))['t'] or 0
    nb_en_retard = Facture.objects.filter(statut='en_retard').count()

    return {
        "ca_periode": ca_periode,
        "cout_sms_periode": cout_sms_periode,
        "repartition_statut": repartition_statut,
        "montant_impaye": montant_impaye,
        "nb_en_retard": nb_en_retard,
    }



""" def kpis_juridiques():
    aujourdhui = timezone.now().date()

    total_dossiers = Dossier.objects.count()
    dossiers_actifs = Dossier.objects.exclude(statut__in=['clos', 'archive']).count()

    echeances_a_risque = (
        Dossier.objects
        .exclude(statut__in=['clos', 'archive'])
        .filter(date_prochaine_echeance__gte=aujourdhui, date_prochaine_echeance__lte=aujourdhui + timedelta(days=7))
        .count()
    )
    echeances_depassees = (
        Dossier.objects
        .exclude(statut__in=['clos', 'archive'])
        .filter(date_prochaine_echeance__lt=aujourdhui)
        .count()
    )

    libelles_type = dict(Dossier.TypeAffaire.choices)
    repartition_type = [
        {"libelle": libelles_type.get(r['type_affaire'], r['type_affaire']), "total": r['total']}
        for r in Dossier.objects.values('type_affaire').annotate(total=Count('id')).order_by('-total')
    ]
    max_type = max((r['total'] for r in repartition_type), default=1)
    for r in repartition_type:
        r['pourcentage'] = round((r['total'] / max_type) * 100)

    top_clients = [
        {"nom": r['client__nom'] or r['client__raison_sociale'] or 'Client', "total": r['total']}
        for r in Dossier.objects.values('client__nom', 'client__raison_sociale')
                 .annotate(total=Count('id')).order_by('-total')[:5]
    ]
    max_client = max((c['total'] for c in top_clients), default=1)
    for c in top_clients:
        c['pourcentage'] = round((c['total'] / max_client) * 100)

    return {
        "total_dossiers": total_dossiers,
        "dossiers_actifs": dossiers_actifs,
        "echeances_a_risque": echeances_a_risque,
        "echeances_depassees": echeances_depassees,
        "repartition_type": repartition_type,
        "top_clients": top_clients,
    }


def kpis_secretariat():
    aujourdhui = timezone.now().date()
    debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())
    fin_semaine = debut_semaine + timedelta(days=6)
    debut_mois = aujourdhui.replace(day=1)

    nouveaux_clients_mois = Client.objects.filter(created_at__gte=debut_mois).count()
    evenements_semaine = EvenementAgenda.objects.filter(date_heure__date__range=(debut_semaine, fin_semaine)).count()
    evenements_critiques_a_venir = EvenementAgenda.objects.filter(critique=True, date_heure__date__gte=aujourdhui).count()

    sms = SMSDetailDestinataire.objects.aggregate(
        total=Count('id'),
        livres=Count('id', filter=Q(status='DELIVERY_SUCCESS')),
    )
    taux_livraison_sms = round((sms['livres'] / sms['total'] * 100), 1) if sms['total'] else 0

    return {
        "nouveaux_clients_mois": nouveaux_clients_mois,
        "evenements_semaine": evenements_semaine,
        "evenements_critiques_a_venir": evenements_critiques_a_venir,
        "sms_total": sms['total'],
        "sms_taux_livraison": taux_livraison_sms,
    }


def kpis_comptable():
    aujourdhui = timezone.now().date()
    debut_mois = aujourdhui.replace(day=1)
    debut_annee = aujourdhui.replace(month=1, day=1)

    ca_mois = Facture.objects.filter(date_emission__gte=debut_mois, statut='payee').aggregate(t=Sum('montant_ttc'))['t'] or 0
    ca_annee = Facture.objects.filter(date_emission__gte=debut_annee, statut='payee').aggregate(t=Sum('montant_ttc'))['t'] or 0
    montant_impaye = Facture.objects.exclude(statut='payee').aggregate(t=Sum('montant_ttc'))['t'] or 0
    nb_en_retard = Facture.objects.filter(statut='en_retard').count()

    libelles_statut = dict(Facture.StatutFacture.choices) if hasattr(Facture, 'StatutFacture') else {}
    repartition_statut = [
        {"libelle": libelles_statut.get(r['statut'], r['statut']), "total": r['total'], "montant": r['montant'] or 0}
        for r in Facture.objects.values('statut').annotate(total=Count('id'), montant=Sum('montant_ttc')).order_by('-montant')
    ]

    cout_sms_mois = SMSGroupEnvoi.objects.filter(created_at__gte=debut_mois).aggregate(t=Sum('cost'))['t'] or 0

    return {
        "ca_mois": ca_mois,
        "ca_annee": ca_annee,
        "montant_impaye": montant_impaye,
        "nb_en_retard": nb_en_retard,
        "repartition_statut": repartition_statut,
        "cout_sms_mois": cout_sms_mois,
    } """
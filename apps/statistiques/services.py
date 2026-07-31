from datetime import timedelta
from django.db.models import Count, Sum, Q
from django.utils import timezone

from dossier.models import Dossier
from client.models import Client
from agenda.models import EvenementAgenda
from facturation.models import Facture
from notifications.models import SMSDetailDestinataire, SMSGroupEnvoi


def kpis_juridiques():
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
    }

from django.db.models import Count, Q
from django.db.models.functions import TruncWeek, TruncMonth, TruncYear
from datetime import date
from django.utils import timezone


from dossier.models import Dossier
from agenda.models import EvenementAgenda

# Couleurs alignées sur les badges déjà utilisés dans dossier_dashboard.html
""" COULEURS_STATUT = {
    'ouvert': '#2563eb',    # blue-600
    'en_cours': '#f59e0b',  # amber-500
    'plaide': '#dc2626',    # red-600
    'clos': '#059669',      # emerald-600
    'archive': '#9ca3af',   # gray-400
} """
""" class DashboardMetricsService:
    @staticmethod
    def obtenir_donnees_graphiques():
               # Graphique 1 : Répartition des Dossiers par Statut (Ouvert, En cours, Plaidé, Clos, Archivé)
        stats_dossiers = (
            Dossier.objects.values('statut')
            .annotate(total=Count('id'))
            .order_by('statut')
        )

        # Graphique 2 : Répartition des Factures par Statut (Brouillon, Envoyée, Payée, En retard)
        # Note : On s'appuie sur le modèle Facture hébergé dans l'application facturation
        stats_factures = (
            Facture.objects.values('statut')
            .annotate(total=Count('id'))
            .order_by('statut')
        )

        return {
            "graphique_dossiers": list(stats_dossiers),
            "graphique_factures": list(stats_factures)
        } """

COULEURS_STATUT = {
    'ouvert': '#2563eb', 'en_cours': '#f59e0b', 'plaide': '#dc2626',
    'clos': '#059669', 'archive': '#9ca3af',
}
MOIS_FR = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']



def stats_dossiers_par_statut():
    ordre = [c[0] for c in Dossier.StatutDossier.choices]
    libelles = dict(Dossier.StatutDossier.choices)
    compte = dict(Dossier.objects.values('statut').annotate(total=Count('id')).values_list('statut', 'total'))
    valeurs = [compte.get(s, 0) for s in ordre]
    return {
        "labels": [libelles[s] for s in ordre],
        "valeurs": valeurs,
        "couleurs": [COULEURS_STATUT[s] for s in ordre],
        "total_general": sum(valeurs),          # = Dossier.objects.count()
        "pagination": {"page": 1, "nb_pages": 1},
    }


def stats_dossiers_par_avocat(page=1, page_size=8):
    # Aucune exclusion : le total DOIT rester identique à stats_dossiers_par_statut.
    # Les dossiers sans avocat assigné sont regroupés sous "Non assigné" plutôt qu'exclus.
    base_qs = (
        Dossier.objects
        .values('avocat_referent_id', 'avocat_referent__first_name', 'avocat_referent__last_name', 'avocat_referent__username')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    total_general = Dossier.objects.count()
    total_categories = base_qs.count()
    nb_pages = max((total_categories + page_size - 1) // page_size, 1)
    page = max(1, min(page, nb_pages))
    page_qs = base_qs[(page - 1) * page_size: page * page_size]

    labels, usernames, valeurs = [], [], []
    for r in page_qs:
        if r['avocat_referent_id'] is None:
            labels.append('Non assigné')
            usernames.append('non_assigné')
        else:
            nom_complet = f"{r['avocat_referent__first_name']} {r['avocat_referent__last_name']}".strip()
            labels.append(nom_complet or r['avocat_referent__username'])
            usernames.append(r['avocat_referent__username'])
        valeurs.append(r['total'])

    return {
        "labels": labels, "usernames": usernames, "valeurs": valeurs,
        "total_general": total_general,          # identique quelle que soit la page affichée
        "pagination": {"page": page, "nb_pages": nb_pages},
    }


def annees_disponibles_agenda():
    annees = sorted({
        d.year for d in EvenementAgenda.objects
        .annotate(a=TruncYear('date_heure')).values_list('a', flat=True).distinct() if d
    }, reverse=True)
    return annees or [timezone.now().year]


def stats_agenda(vue='mois', annee=None, page=1, page_size=9):
    aujourdhui = timezone.now().date()

    if vue == 'annee':
        lignes = list(
            EvenementAgenda.objects
            .annotate(p=TruncYear('date_heure')).values('p')
            .annotate(total=Count('id'), critiques=Count('id', filter=Q(critique=True)))
            .order_by('-p')
        )
        nb_pages = max((len(lignes) + page_size - 1) // page_size, 1)
        page = max(1, min(page, nb_pages))
        page_lignes = lignes[(page - 1) * page_size: page * page_size]
        page_lignes.reverse()
        return {
            "labels": [str(r['p'].year) for r in page_lignes],
            "normaux": [r['total'] - r['critiques'] for r in page_lignes],
            "critiques": [r['critiques'] for r in page_lignes],
            "index_actuel": None,
            "total_general": EvenementAgenda.objects.count(),
            "pagination": {"page": page, "nb_pages": nb_pages},
        }

    annee = annee or aujourdhui.year
    total_annee = EvenementAgenda.objects.filter(date_heure__year=annee).count()

    if vue == 'mois':
        compte = {
            r['p'].month: r for r in (
                EvenementAgenda.objects.filter(date_heure__year=annee)
                .annotate(p=TruncMonth('date_heure')).values('p')
                .annotate(total=Count('id'), critiques=Count('id', filter=Q(critique=True)))
            )
        }
        labels, normaux, critiques = [], [], []
        for m in range(1, 13):  # les 12 mois toujours affichés, même sans données
            r = compte.get(m)
            labels.append(MOIS_FR[m - 1])
            normaux.append((r['total'] - r['critiques']) if r else 0)
            critiques.append(r['critiques'] if r else 0)
        index_actuel = (aujourdhui.month - 1) if annee == aujourdhui.year else None
        return {
            "labels": labels, "normaux": normaux, "critiques": critiques,
            "index_actuel": index_actuel,
            "total_general": total_annee,
            "pagination": {"page": 1, "nb_pages": 1},  # 12 mois fixes, jamais paginé
        }

    # vue == 'semaine'
    semaine_actuelle = aujourdhui.isocalendar()[1]
    nb_semaines_annee = date(annee, 12, 28).isocalendar()[1]
    taille_bloc = 9  # fenêtre affichée (4 semaines avant/après le centre)

    nb_pages = max((nb_semaines_annee + taille_bloc - 1) // taille_bloc, 1)
    page = max(1, min(page, nb_pages))

    if page == 1:
        centre = semaine_actuelle if annee == aujourdhui.year else nb_semaines_annee // 2
        debut_bloc = max(1, centre - 4)
    else:
        debut_bloc = (page - 1) * taille_bloc + 1
    fin_bloc = min(nb_semaines_annee, debut_bloc + taille_bloc - 1)

    qs = (
        EvenementAgenda.objects.filter(date_heure__year=annee)
        .annotate(p=TruncWeek('date_heure')).values('p')
        .annotate(total=Count('id'), critiques=Count('id', filter=Q(critique=True)))
    )
    compte_semaine = {r['p'].isocalendar()[1]: r for r in qs}

    labels, normaux, critiques = [], [], []
    index_actuel = None
    for i, num in enumerate(range(debut_bloc, fin_bloc + 1)):
        r = compte_semaine.get(num)
        labels.append(f"S{num}")
        normaux.append((r['total'] - r['critiques']) if r else 0)
        critiques.append(r['critiques'] if r else 0)
        if annee == aujourdhui.year and num == semaine_actuelle:
            index_actuel = i

    return {
        "labels": labels, "normaux": normaux, "critiques": critiques,
        "index_actuel": index_actuel,
        "total_general": total_annee,
        "pagination": {"page": page, "nb_pages": nb_pages},
    }


""" def stats_dossiers_par_statut():
    ordre = [c[0] for c in Dossier.StatutDossier.choices]
    libelles = dict(Dossier.StatutDossier.choices)
    compte = dict(Dossier.objects.values('statut').annotate(total=Count('id')).values_list('statut', 'total'))
    return {
        "labels": [libelles[s] for s in ordre],
        "valeurs": [compte.get(s, 0) for s in ordre],
        "couleurs": [COULEURS_STATUT[s] for s in ordre],
        "pagination": {"page": 1, "nb_pages": 1},  # nombre de statuts fixe : jamais paginé
    }



def stats_dossiers_par_avocat(page=1, page_size=8):
    qs = (
        Dossier.objects
        .exclude(avocat_referent__isnull=True)
        .exclude(statut__in=['clos', 'archive'])
        .values('avocat_referent__first_name', 'avocat_referent__last_name', 'avocat_referent__username')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    total_avocats = qs.count()
    nb_pages = max((total_avocats + page_size - 1) // page_size, 1)
    page = max(1, min(page, nb_pages))
    page_qs = qs[(page - 1) * page_size: page * page_size]

    return {
        "labels": [f"{r['avocat_referent__first_name']} {r['avocat_referent__last_name']}".strip() for r in page_qs],
        "usernames": [r['avocat_referent__username'] for r in page_qs],
        "valeurs": [r['total'] for r in page_qs],
        "pagination": {"page": page, "nb_pages": nb_pages},
    }


def stats_agenda_par_periode(periode='mois', page=1, page_size=8):
    trunc_fn = {'semaine': TruncWeek, 'mois': TruncMonth, 'annee': TruncYear}.get(periode, TruncMonth)
    qs = (
        EvenementAgenda.objects
        .annotate(periode_bucket=trunc_fn('date_heure'))
        .values('periode_bucket')
        .annotate(total=Count('id'), critiques=Count('id', filter=Q(critique=True)))
        .order_by('-periode_bucket')  # le plus récent en premier, pour paginer vers l'historique
    )
    total_buckets = qs.count()
    nb_pages = max((total_buckets + page_size - 1) // page_size, 1)
    page = max(1, min(page, nb_pages))
    page_qs = list(qs[(page - 1) * page_size: page * page_size])
    page_qs.reverse()  # remis en ordre chronologique croissant pour l'affichage

    return {
        "labels": [_formater_periode(r['periode_bucket'], periode) for r in page_qs],
        "normaux": [r['total'] - r['critiques'] for r in page_qs],
        "critiques": [r['critiques'] for r in page_qs],
        "pagination": {"page": page, "nb_pages": nb_pages},
    }


def _formater_periode(date_bucket, periode):
    if date_bucket is None:
        return "—"
    if periode == 'semaine':
        return f"Sem. {date_bucket.isocalendar()[1]}"
    if periode == 'annee':
        return str(date_bucket.year)
    mois_fr = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
    return f"{mois_fr[date_bucket.month - 1]} {date_bucket.year}" """


"""  """

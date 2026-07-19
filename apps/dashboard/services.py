from django.db.models import Count
from dossier.models import Dossier
from facturation.models import Facture

class DashboardMetricsService:
    @staticmethod
    def obtenir_donnees_graphiques():
        """
        Calcule uniquement les agrégats chiffrés pour les graphiques du tableau de bord.
        ZÉRO donnée confidentielle ou superflue n'est transférée sur le réseau.
        """
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
        }

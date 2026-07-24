# management/commands/relancer_delai_critiques.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = "Vérifie les délais de procédure sur le point d'arriver à forclusion"

    def handle(self, *args, **options):
        aujourdhui = timezone.now().date()
        
        # 1. Sélectionner les événements de type DELAI_PROCEDURE non traités
        delais_en_cours = EvenementAgenda.objects.filter(
            type=EvenementAgenda.TypeEvenement.DELAI_PROCEDURE,
            statut_traitement=EvenementAgenda.StatutTraitement.EN_ATTENTE,
            date_echeance_calculee__isnull=False
        )

        for evt in delais_en_cours:
            jours_restants = (evt.date_echeance_calculee.date() - aujourdhui).days

            if jours_restants <= 0:
                evt.statut_traitement = EvenementAgenda.StatutTraitement.FORCLOS
                evt.save()
                # Déclencher notification d'urgence extrême au cabinet
            elif jours_restants in [15, 7, 3, 1]:
                # Déclencher Rappel N°1, Rappel N°2 ou DERNIER RAPPEL selon jours_restants
                self.envoyer_notification_rappel(evt, jours_restants)

    def envoyer_notification_rappel(self, evt, jours_restants):
        # Logique d'envoi d'Email / SMS / Notification In-App
        niveau = "DERNIER RAPPEL" if jours_restants <= 3 else "RAPPEL"
        print(f"[{niveau}] Dossier {evt.dossier.reference} : {evt.titre} expire dans {jours_restants} jours !")
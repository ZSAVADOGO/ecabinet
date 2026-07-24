import uuid
from django.db import models
from client.models import AuditableModel
from dossier.models import Dossier
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from django.core.exceptions import ValidationError

class RolePartiePrenante(models.TextChoices):
    CLIENT = 'client', 'Client'
    AVOCAT_REFERENT = 'avocat_referent', 'Avocat référent'
    AVOCAT_ADVERSE = 'avocat_adverse', 'Avocat adverse'
    TEMOIN = 'temoin', 'Témoin'
    HUISSIER = 'huissier', 'Huissier'
    EXPERT = 'expert', 'Expert judiciaire'
    AUTRE = 'autre', 'Autre'


class PartiePrenante(AuditableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    #dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='parties_prenantes')
     # 🌟 OPTIMISATION CRITIQUE : Autorise null=True pour le cloisonnement de l'agenda
    dossier = models.ForeignKey(
        Dossier, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='parties_prenantes'
    )
    nom = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=RolePartiePrenante.choices)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    notifiable = models.BooleanField(default=True, help_text="Reçoit les rappels d'agenda de ce dossier")
    notes = models.TextField(null=True, blank=True)  # était CharField(255, db_index=True)

    class Meta:
        db_table = 'parties_prenantes'

class EvenementAgenda(AuditableModel):

    class TypeEvenement(models.TextChoices):
        AUDIENCE = 'audience', 'Audience'
        RDV_CLIENT = 'rdv_client', 'Rendez-vous Client'
        DELAI_PROCEDURE = 'delai_procedure', 'Délai Procédure'
        DELIBERE = 'delibere', 'Prompt / Délibéré'
        DEMARCHE_EXTERNE = 'demarche_externe', 'Démarche Greffe / Huissier'
        AUTRE = 'autre', 'Autre'

    class TypeDelaiProcedure(models.TextChoices):
        APPEL = 'appel', 'Appel'
        POURVOI_CASSATION = 'pourvoi', 'Pourvoi en cassation'
        OPPOSITION = 'opposition', 'Opposition'
        TIERCE_OPPOSITION = 'tierce_opposition', 'Tierce opposition'
        EXECUTION = 'execution', "Délai d'exécution"
        MEMOIRE = 'memoire', 'Dépôt de mémoire / Conclusions'
        AUTRE = 'autre', 'Autre délai'

    class StatutTraitement(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        TRAITE = 'traite', 'Traité dans les délais'
        RENVOYE = 'renvoye', 'Renvoyé à une autre date'
        FORCLOS = 'forclos', 'Forclos / délai dépassé'
        AUTRE = 'autre', 'Autre'

    class MotifRenvoi(models.TextChoices):
        COMMUNICATION_PIECES = 'comm_pieces', 'Pour communication de pièces'
        REPLIQUE = 'replique', 'Pour réplique / conclusions'
        PLAIDOIRIE = 'plaidoirie', 'Pour plaidoiries'
        COMPOSITION_TRIBUNAL = 'composition', 'Composition de la juridiction'
        PAIEMENT_CONSIGNATION = 'consignation', 'Paiement de consignation'
        AUTRE = 'autre', 'Autre motif'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TypeEvenement.choices, default=TypeEvenement.AUTRE, db_index=True)
    type_delai = models.CharField(max_length=25, choices=TypeDelaiProcedure.choices, null=True, blank=True)

    date_heure = models.DateTimeField(db_index=True)

    date_echeance_calculee = models.DateTimeField(null=True, blank=True, db_index=True, help_text="Date limite légale recalculée")  
    date_declencheur = models.DateField(null=True, blank=True, help_text="Ex: date de signification du jugement")
    duree_legale_jours = models.PositiveIntegerField(null=True, blank=True)


    critique = models.BooleanField(default=False)

    statut_traitement = models.CharField(max_length=20, choices=StatutTraitement.choices, default=StatutTraitement.EN_ATTENTE)
    motif_renvoi = models.CharField(max_length=20, choices=MotifRenvoi.choices, null=True, blank=True) # 🌟 RESTITUTION DU CHAMP MANQUANT

    description = models.TextField(null=True, blank=True)  # était CharField(255, db_index=True)

    dossier = models.ForeignKey(Dossier, on_delete=models.PROTECT, null=True, blank=True, related_name='evenements')

    responsables = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='evenements_agenda',
        blank=True,
        help_text="Avocats ou collaborateurs responsables d'assurer l'événement"
    )
    
    parties_prenantes = models.ManyToManyField(
        PartiePrenante,
        related_name='evenements',
        blank=True,
        help_text="Parties prenantes associées à cet événement"
        )
    # Juridiction spécifique (Si différente de celle du dossier)
    tribunal = models.ForeignKey('authentication.Tribunal', on_delete=models.SET_NULL, null=True, blank=True)
    chambre = models.ForeignKey('authentication.Chambre', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'evenements_agenda'
        ordering = ['date_heure']

    def save(self, *args, **kwargs):
        # Sécurité : Si l'événement touche un délai de recours, il devient automatiquement CRITIQUE
        if self.type == self.TypeEvenement.DELAI_PROCEDURE:
            self.critique = True
            
        # Calcul automatique indicatif de l'échéance
        if self.date_declencheur and self.duree_legale_jours:
            # Note pour évolution : Vous pourrez y injecter un helper pour la gestion des Jours Francs
            base_date = self.date_declencheur + timedelta(days=self.duree_legale_jours)
            self.date_echeance_calculee = timezone.make_aware(
                timezone.datetime.combine(base_date, timezone.datetime.min.time())
            )
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # Si nous sommes dans un formulaire Django classique ou l'Admin
        if hasattr(self, 'cleaned_data') and 'parties_prenantes' in self.cleaned_data:
            parties_selectionnees = self.cleaned_data['parties_prenantes']
            if self.dossier:
                for pp in parties_selectionnees:
                    if pp.dossier_id != self.dossier_id:
                        raise ValidationError(
                            f"La partie prenante « {pp.nom} » n'appartient pas au dossier associé à cet événement."
                        )

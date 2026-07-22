import uuid
from django.db import models
from client.models import AuditableModel
from dossier.models import Dossier

class EvenementAgenda(AuditableModel):
    class TypeEvenement(models.TextChoices):
        AUDIENCE = 'audience', 'Audience'
        RDV_CLIENT = 'rdv_client', 'Rendez-vous Client'
        DELAI_PROCEDURE = 'delai_procedure', 'Délai Procédure'
        AUTRE = 'autre', 'Autre'

    class TypeDelaiProcedure(models.TextChoices):
        APPEL = 'appel', 'Appel'
        POURVOI_CASSATION = 'pourvoi', 'Pourvoi en cassation'
        OPPOSITION = 'opposition', 'Opposition'
        TIERCE_OPPOSITION = 'tierce_opposition', 'Tierce opposition'
        EXECUTION = 'execution', "Délai d'exécution"
        AUTRE = 'autre', 'Autre délai'

    class StatutTraitement(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        TRAITE = 'traite', 'Traité dans les délais'
        FORCLOS = 'forclos', 'Forclos / délai dépassé'

    
    """ id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TypeEvenement.choices, default=TypeEvenement.AUTRE, db_index=True)
    # sur EvenementAgenda, uniquement si type == DELAI_PROCEDURE :
    type_delai = models.CharField(max_length=25, choices=TypeDelaiProcedure.choices, null=True, blank=True)
    date_heure = models.DateTimeField(db_index=True)
    critique = models.BooleanField(default=False)  # Forclusion -> Alerte renforcée
    description = models.CharField(max_length=255, db_index=True, null=True, blank=True)

    date_declencheur = models.DateField(null=True, blank=True, help_text="Ex: date de signification du jugement")
    duree_legale_jours = models.PositiveIntegerField(null=True, blank=True)
    statut_traitement = models.CharField(max_length=20, choices=StatutTraitement.choices, default=StatutTraitement.EN_ATTENTE)

    dossier = models.ForeignKey(Dossier, on_delete=models.PROTECT, null=True, blank=True, related_name='evenements') """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TypeEvenement.choices, default=TypeEvenement.AUTRE, db_index=True)
    type_delai = models.CharField(max_length=25, choices=TypeDelaiProcedure.choices, null=True, blank=True)
    date_heure = models.DateTimeField(db_index=True)
    date_declencheur = models.DateField(null=True, blank=True, help_text="Ex: date de signification du jugement")
    duree_legale_jours = models.PositiveIntegerField(null=True, blank=True)
    critique = models.BooleanField(default=False)
    statut_traitement = models.CharField(max_length=20, choices=StatutTraitement.choices, default=StatutTraitement.EN_ATTENTE)
    description = models.TextField(null=True, blank=True)  # était CharField(255, db_index=True)

    dossier = models.ForeignKey(Dossier, on_delete=models.PROTECT, null=True, blank=True, related_name='evenements')


    class Meta:
        db_table = 'evenements_agenda'

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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TypeEvenement.choices, default=TypeEvenement.AUTRE, db_index=True)
    date_heure = models.DateTimeField(db_index=True)
    critique = models.BooleanField(default=False)  # Forclusion -> Alerte renforcée
    description = models.CharField(max_length=255, db_index=True, null=True, blank=True)


    # Jointure avec Dossier (onDelete: CASCADE, nullable: true)
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, null=True, blank=True, related_name='evenements')

    class Meta:
        db_table = 'evenements_agenda'

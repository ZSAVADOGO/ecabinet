import uuid
from django.db import models
from client.models import AuditableModel
from dossier.models import Dossier

class DocumentEntity(AuditableModel):
    class TypeDocument(models.TextChoices):
        CONTRAT = 'contrat', 'Contrat'
        CONCLUSION = 'conclusion', 'Conclusion'
        JUGEMENT = 'jugement', 'Jugement'
        PIECE_ADVERSE = 'piece_adverse', 'Pièce Adverse'
        COURRIER = 'courrier', 'Courrier'
        AUTRE = 'autre', 'Autre'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TypeDocument.choices, default=TypeDocument.AUTRE, db_index=True)
    chemin_stockage = models.CharField(max_length=500)  # Lien vers stockage (S3 ou local)
    version = models.IntegerField(default=1)

    # Jointure avec Dossier (onDelete: CASCADE)
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='documents')

    class Meta:
        db_table = 'documents'

import uuid
from django.db import models
from client.models import Client, AuditableModel
from dossier.models import Dossier

class Facture(AuditableModel):
    class StatutFacture(models.TextChoices):
        BROUILLON = 'brouillon', 'Brouillon'
        ENVOYEE = 'envoyee', 'Envoyée'
        PAYEE = 'payee', 'Payée'
        EN_RETARD = 'en_retard', 'En retard'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=50, unique=True, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.RESTRICT, related_name='factures')
    dossier = models.ForeignKey(Dossier, on_delete=models.SET_NULL, null=True, blank=True, related_name='factures')
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2)
    montant_ttc  = models.DecimalField(max_digits=10, decimal_places=2)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    statut = models.CharField(max_length=20, choices=StatutFacture.choices, default=StatutFacture.BROUILLON, db_index=True)
    date_emission = models.DateField()
    date_echeance = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255, db_index=True, null=True, blank=True)

    class Meta:
        db_table = 'factures'

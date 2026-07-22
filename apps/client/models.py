import uuid
from django.db import models
from django.conf import settings

from django.core.exceptions import ValidationError  # Résout "ValidationError" is not defined

# Classe mère de traçabilité globale
class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_creations')
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_modifications')

    class Meta:
        abstract = True

class Client(AuditableModel):
    class ClientType(models.TextChoices):
        PERSONNE_PHYSIQUE = 'personne_physique', 'Personne Physique'
        PERSONNE_MORALE = 'personne_morale', 'Personne Morale'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=ClientType.choices, default=ClientType.PERSONNE_PHYSIQUE, db_index=True)
    nom = models.CharField(max_length=255,null=True, blank=True, db_index=True)
    prenom = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # <-- Ajouté ici
    raison_sociale = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # <-- Ajouté ici   ifu_rccm = models.CharField(max_length=20, null=True, blank=True)  # Spécifique personnes morales
    ifu_rccm = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    telephone1 = models.CharField(max_length=30)
    telephone2 = models.CharField(max_length=30, null=True, blank=True)
    adresse = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    #class Meta:
    #    db_table = 'clients'

    class Meta:
        db_table = 'clients'
        indexes = [
            models.Index(fields=['nom', 'prenom']),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(type='personne_physique', nom__isnull=False) |
                    models.Q(type='personne_morale', raison_sociale__isnull=False)
                ),
                name='client_nom_ou_raison_sociale_requis'
            )
        ]

    def clean(self):
        if self.type == self.ClientType.PERSONNE_PHYSIQUE and not self.nom:
            raise ValidationError("Le nom est requis pour une personne physique.")
        if self.type == self.ClientType.PERSONNE_MORALE and not self.raison_sociale:
            raise ValidationError("La raison sociale est requise pour une personne morale.")

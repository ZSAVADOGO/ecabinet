import uuid
from django.db import models
from django.conf import settings

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
    #nom_complet = models.CharField(max_length=255, db_index=True)
    nom = models.CharField(max_length=255,null=True, blank=True, db_index=True)
    prenom = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # <-- Ajouté ici
    raison_sociale = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # <-- Ajouté ici   ifu_rccm = models.CharField(max_length=20, null=True, blank=True)  # Spécifique personnes morales
    ifu_rccm = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    telephone1 = models.CharField(max_length=30)
    telephone2 = models.CharField(max_length=30, null=True, blank=True)
    adresse = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'clients'

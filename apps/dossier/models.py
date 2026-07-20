import uuid
from django.db import models
from django.conf import settings
from client.models import Client, AuditableModel

from django.utils import timezone  # Résout "timezone" is not defined


class Dossier(AuditableModel):
    class StatutDossier(models.TextChoices):
        OUVERT = 'ouvert', 'Ouvert'
        EN_COURS = 'en_cours', 'En cours'
        PLAIDE = 'plaide', 'Plaidé'
        CLOS = 'clos', 'Clos'
        ARCHIVE = 'archive', 'Archivé'

    class TypeAffaire(models.TextChoices):
        CIVIL = 'civil', 'Civil'
        PENAL = 'penal', 'Pénal'
        COMMERCIAL = 'commercial', 'Commercial'
        SOCIAL = 'social', 'Social'
        FAMILLE = 'famille', 'Famille'
        ADMINISTRATIF = 'administratif', 'Administratif'
        AUTRE = 'autre', 'Autre'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, db_index=True)  # ex: DOS-2026-0001
    intitule = models.CharField(max_length=255)
    type_affaire = models.CharField(max_length=20, choices=TypeAffaire.choices, default=TypeAffaire.AUTRE, db_index=True)
    statut = models.CharField(max_length=20, choices=StatutDossier.choices, default=StatutDossier.OUVERT, db_index=True)

    # Jointure avec Client (onDelete: 'RESTRICT')
    client = models.ForeignKey(Client, on_delete=models.RESTRICT, related_name='dossiers')

    # Jointure avec l'Avocat Référent (User)
    avocat_referent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_referes')

    juridiction = models.CharField(max_length=255, null=True, blank=True)
    date_ouverture = models.DateField(null=True, blank=True)
    date_prochaine_echeance = models.DateField(null=True, blank=True, db_index=True)  # Délai de procédure critique
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'dossiers'
    
    # models.py (Dossier) — génération auto de la référence
    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            dernier = Dossier.objects.filter(reference__startswith=f'DOS-{annee}-').order_by('-reference').first()
            n = int(dernier.reference.split('-')[-1]) + 1 if dernier else 1
            self.reference = f'DOS-{annee}-{n:04d}'
        super().save(*args, **kwargs)

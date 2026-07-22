import uuid
from django.db import models
from django.conf import settings
from client.models import Client, AuditableModel

from apps.authentication.models import Chambre

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

    class DegreInstance(models.TextChoices):
        PREMIERE_INSTANCE = 'premiere_instance', 'Première instance'
        APPEL = 'appel', 'Appel'
        CASSATION = 'cassation', 'Cassation'


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    """ reference = models.CharField(max_length=50, unique=True, db_index=True)  # ex: DOS-2026-0001
    intitule = models.CharField(max_length=255)
    type_affaire = models.CharField(max_length=20, choices=TypeAffaire.choices, default=TypeAffaire.AUTRE, db_index=True)
    statut = models.CharField(max_length=20, choices=StatutDossier.choices, default=StatutDossier.OUVERT, db_index=True)

    # Jointure avec Client (onDelete: 'RESTRICT')
    client = models.ForeignKey(Client, on_delete=models.RESTRICT, related_name='dossiers')
   
    # Jointure avec l'Avocat Référent (User)
    avocat_referent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_referes')
    degre_instance = models.CharField(max_length=20, choices=DegreInstance.choices, default=DegreInstance.PREMIERE_INSTANCE)
    dossier_origine = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_recours')

    juridiction = models.CharField(max_length=255, null=True, blank=True)
    # Remplace l'ancien "juridiction = CharField(...)"
    tribunal = models.ForeignKey(
        'authentication.Tribunal',   # adapte le nom d'app selon où Tribunal est réellement défini
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='dossiers',
    )
    partie_adverse = models.CharField(max_length=255, blank=True, null=True)
    numero_role = models.CharField(max_length=50, blank=True, null=True, db_index=True)

    chambre = models.ForeignKey(Chambre, on_delete=models.SET_NULL, null=True, blank=True)
    juge_en_charge = models.CharField(max_length=150, blank=True, null=True)
    numero_bureau = models.CharField(max_length=20, blank=True, null=True)

    date_ouverture = models.DateField(null=True, blank=True)
    date_prochaine_echeance = models.DateField(null=True, blank=True, db_index=True)  # Délai de procédure critique
    description = models.TextField(null=True, blank=True) """
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    numero_role = models.CharField(max_length=50, blank=True, null=True, db_index=True,
                                    help_text="Numéro de rôle/RG attribué par le greffe")
    intitule = models.CharField(max_length=255)
    type_affaire = models.CharField(max_length=20, choices=TypeAffaire.choices, default=TypeAffaire.AUTRE, db_index=True)
    statut = models.CharField(max_length=20, choices=StatutDossier.choices, default=StatutDossier.OUVERT, db_index=True)
    degre_instance = models.CharField(max_length=20, choices=DegreInstance.choices, default=DegreInstance.PREMIERE_INSTANCE)
    dossier_origine = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_recours')
    juridiction = models.CharField(max_length=255, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.RESTRICT, related_name='dossiers')
    avocat_referent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_referes')

    partie_adverse = models.CharField(max_length=255, blank=True, null=True)
    avocat_adverse = models.CharField(max_length=255, blank=True, null=True)

    tribunal = models.ForeignKey('authentication.Tribunal', on_delete=models.PROTECT, null=True, blank=True, related_name='dossiers')
    chambre = models.ForeignKey('authentication.Chambre', on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers')
    juge_en_charge = models.CharField(max_length=150, blank=True, null=True)
    numero_bureau = models.CharField(max_length=20, blank=True, null=True)

    date_ouverture = models.DateField(null=True, blank=True)
    date_prochaine_echeance = models.DateField(null=True, blank=True, db_index=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'dossiers'
    
    # models.py (Dossier) — génération auto de la référence
    """ def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            dernier = Dossier.objects.filter(reference__startswith=f'DOS-{annee}-').order_by('-reference').first()
            n = int(dernier.reference.split('-')[-1]) + 1 if dernier else 1
            self.reference = f'DOS-{annee}-{n:04d}'
        super().save(*args, **kwargs) """

    def save(self, *args, **kwargs):
        # On génère ou recalcule la référence uniquement s'il s'agit d'une création (pas d'un update)
        if not self.pk:
            annee = timezone.now().year
            prefixe = f'DOS-{annee}-'
            
            # 1. PROTECTION CONCURRENCE : select_for_update() bloque l'accès concurrent au compteur 
            # pendant la milliseconde où le save s'exécute.
            dernier = Dossier.objects.select_for_update().filter(
                reference__startswith=prefixe
            ).order_by('-reference').first()
            
            if dernier:
                try:
                    n = int(dernier.reference.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    n = 1
            else:
                n = 1
                
            # 2. RESOLUTION DU CONFLIT UI : On écrase TOUJOURS la valeur estimée envoyée par le frontend
            # avec le numéro séquentiel réel et disponible en BDD.
            self.reference = f'{prefixe}{n:04d}'

        super().save(*args, **kwargs)

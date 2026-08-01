import uuid
from django.db import models
from django.conf import settings
from client.models import Client, AuditableModel

#from dossier.models import Chambre

from django.utils import timezone  # Résout "timezone" is not defined



# ==========================================
# 2. ENTITÉ TYPE DE TRIBUNAL (ÉVOLUTIF)
# ==========================================
class TypeTribunal(models.Model):
    """
    Permet au cabinet d'ajouter/modifier des types de juridictions sans toucher au code.
    Ex: 'TJ' -> Tribunal Judiciaire, 'TC' -> Tribunal de Commerce, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=15, unique=True, help_text="Ex: 'TJ', 'TC', 'CA'")
    libelle = models.CharField(max_length=150, help_text="Ex: 'Tribunal Judiciaire'")
    ordre_affichage = models.PositiveIntegerField(default=0, help_text="Ordre dans les menus déroulants")
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'type_tribunal'
        verbose_name = "Type de Tribunal"
        verbose_name_plural = "Types de Tribunaux"
        ordering = ['ordre_affichage', 'libelle']

    def __str__(self):
        return f"{self.libelle} ({self.code})"


# ==========================================
# 3. ENTITÉ TRIBUNAL / JURIDICTION
# ==========================================
class Tribunal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=255, help_text="Ex: Tribunal Judiciaire de Paris")
    code = models.CharField(
        max_length=20, unique=True, db_index=True, null=True, blank=True,
        help_text="Ex: T.G.I.O — abréviation utilisée dans les documents/courriers"
    )
    # Clé étrangère vers le type évolutif
    type_tribunal = models.ForeignKey(
        TypeTribunal, 
        on_delete=models.PROTECT, 
        related_name="tribunaux",
        db_index=True
    )
    
    adresse = models.TextField(blank=True, null=True)
    code_postal = models.CharField(max_length=10, db_index=True, blank=True, null=True)
    ville = models.CharField(max_length=150, db_index=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email_greffe = models.EmailField(blank=True, null=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'tribunal'
        verbose_name = "Tribunal"
        verbose_name_plural = "Tribunaux"
        ordering = ['ville', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.ville})"

# ==========================================
# . ENTITÉ CHAMBRE
# ==========================================

class Chambre(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tribunal = models.ForeignKey(Tribunal, on_delete=models.CASCADE, related_name='chambres')
    libelle = models.CharField(max_length=150, help_text="Ex: Chambre de Conseil, Correctionnelle, ECOFI")
    notes = models.TextField(null=True, blank=True)
    class Meta:
        db_table = 'chambres'
        verbose_name = "Chambre"
        verbose_name_plural = "Chambres"
        unique_together = ('tribunal', 'libelle')
        ordering = ['tribunal', 'libelle']

    def __str__(self):
        return f"{self.libelle} ({self.tribunal.code})"

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
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    numero_role = models.CharField(max_length=50, blank=True, null=True, db_index=True,
                                    help_text="Numéro de rôle/RG attribué par le greffe")
    intitule = models.CharField(max_length=255)
    type_affaire = models.CharField(max_length=20, choices=TypeAffaire.choices, default=TypeAffaire.AUTRE, db_index=True)
    statut = models.CharField(max_length=20, choices=StatutDossier.choices, default=StatutDossier.OUVERT, db_index=True)
    degre_instance = models.CharField(max_length=20, choices=DegreInstance.choices, default=DegreInstance.PREMIERE_INSTANCE)
    dossier_origine = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_recours')
    #juridiction = models.CharField(max_length=255, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.RESTRICT, related_name='dossiers')
    avocat_referent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_referes')

    partie_adverse = models.CharField(max_length=255, blank=True, null=True)
    avocat_adverse = models.CharField(max_length=255, blank=True, null=True)

    tribunal = models.ForeignKey('dossier.Tribunal', on_delete=models.PROTECT, null=True, blank=True, related_name='dossiers')
    chambre = models.ForeignKey('dossier.Chambre', on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers')
    juge_en_charge = models.CharField(max_length=150, blank=True, null=True)
    numero_bureau = models.CharField(max_length=20, blank=True, null=True)

    date_ouverture = models.DateField(null=True, blank=True)
    date_prochaine_echeance = models.DateField(null=True, blank=True, db_index=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'dossiers'
    
    def save(self, *args, **kwargs):
        if not self.pk:
            annee = timezone.now().year
            prefixe = f'DOS-{annee}-'
            
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
                
            self.reference = f'{prefixe}{n:04d}'

        super().save(*args, **kwargs)

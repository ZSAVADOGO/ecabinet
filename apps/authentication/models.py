import uuid
from datetime import date
from django.db import models
from django.contrib.auth.models import AbstractUser

from django.utils import timezone
from datetime import timedelta



#from apps.authentication.models import Tribunal


# ==========================================
# 1. ENTITÉ SPÉCIALITÉ (Toujours requise pour la relation)
# ==========================================


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

# 1. Specialite

class Specialite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    libelle = models.CharField(max_length=150, unique=True, db_index=True)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'specialite'
        verbose_name = "Spécialité"
        verbose_name_plural = "Spécialités"

    def __str__(self):
        return self.libelle

    
# 2. ENTITÉ UNIQUE USER (FUSIONNÉE)
class User(AbstractUser):
    class UserRole(models.TextChoices):
        ASSOCIE = 'associe', 'Associé'
        AVOCAT = 'avocat', 'Avocat'
        COLLABORATEUR = 'collaborateur', 'Collaborateur'
        SECRETARIAT = 'secretariat', 'Secrétariat'
        STAGIAIRE = 'stagiaire', 'Stagiaire'
        COMPTABLE = 'comptable', 'Comptable'

    # Identifiant unique technique
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Rôle hiérarchique au cabinet
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.COLLABORATEUR,
        db_index=True
    )
    
    # Identification judiciaire & Cabinet
    departement = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: Pôle Pénal, Droit Social")
    notes = models.TextField(null=True, blank=True)

    # Coordonnées professionnelles directes
    telephone_direct = models.CharField(max_length=20, blank=True, null=True)
    telephone2 = models.CharField(max_length=20, blank=True, null=True)
    
    # Éléments financiers (Utile pour valoriser l'agenda et la facturation)
    taux_horaire_defaut = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text="Taux horaire standard HT appliqué pour cet utilisateur"
    )
    
    # Calcul de l'ancienneté
    date_prestation_serment = models.DateField(blank=True, null=True)

    # Métadonnées temporelles
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Identité (Champs explicites demandés, synchronisés avec first/last name de Django)
    last_name = models.CharField(max_length=255, db_index=True, verbose_name="Nom")
    first_name = models.CharField(max_length=255, db_index=True, verbose_name="Prénom")

    email = models.EmailField(unique=True) # Rendu unique pour l'authentification sécurisée

    # Relations du cabinet
    specialites = models.ManyToManyField(Specialite, blank=True, related_name="utilisateurs")

    # Configuration pour utiliser l'email comme identifiant de connexion principal
    USERNAME_FIELD = 'email'
    #REQUIRED_FIELDS = ['username', 'nom', 'prenom']
    REQUIRED_FIELDS = ['username', 'last_name', 'first_name']


# --- Sécurité : anti brute-force ---
    tentatives_echouees = models.PositiveSmallIntegerField(default=0)
    verrouille_jusqu_a = models.DateTimeField(null=True, blank=True)

    # --- Sécurité : hygiène des mots de passe ---
    doit_changer_mot_de_passe = models.BooleanField(
        default=False,
        help_text="Force le changement au prochain login (compte créé par un admin, mot de passe temporaire)."
    )
    date_dernier_changement_mdp = models.DateTimeField(null=True, blank=True)

    # --- Traçabilité ---
    derniere_connexion_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
            db_table = 'users'
            verbose_name = "Utilisateur / Collaborateur"
            verbose_name_plural = "Utilisateurs / Collaborateurs"

    def est_verrouille(self) -> bool:
        return bool(self.verrouille_jusqu_a and self.verrouille_jusqu_a > timezone.now())

    def enregistrer_echec_connexion(self, seuil=5, duree_verrouillage_minutes=15):
        self.tentatives_echouees += 1
        if self.tentatives_echouees >= seuil:
            self.verrouille_jusqu_a = timezone.now() + timedelta(minutes=duree_verrouillage_minutes)
        self.save(update_fields=["tentatives_echouees", "verrouille_jusqu_a"])

    def reinitialiser_tentatives(self, ip=None):
        self.tentatives_echouees = 0
        self.verrouille_jusqu_a = None
        if ip:
            self.derniere_connexion_ip = ip
        self.save(update_fields=["tentatives_echouees", "verrouille_jusqu_a", "derniere_connexion_ip"])


    # 2. LES ALIAS PYTHON (Aucune colonne ne sera créée dans MySQL pour eux)
    @property
    def nom(self) -> str:
        return self.last_name

    @nom.setter
    def nom(self, value: str):
        self.last_name = value

    @property
    def prenom(self) -> str:
        return self.first_name

    @prenom.setter
    def prenom(self, value: str):
        self.first_name = value

    # Calcul dynamique de l'expérience
    @property
    def annees_experience(self) -> int:
        if not self.date_prestation_serment:
            return 0
        aujourdhui = date.today()
        return aujourdhui.year - self.date_prestation_serment.year - (
            (aujourdhui.month, aujourdhui.day) < (self.date_prestation_serment.month, self.date_prestation_serment.day)
        )

    

    def __str__(self):
        nom_complet = f"{self.last_name.upper()} {self.first_name}".strip()
        return f"{nom_complet or self.username} ({self.get_role_display()})"


# Nouveau modèle : journal d'audit des connexions (obligation de traçabilité)
class JournalConnexion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_connexions')
    email_saisi = models.EmailField(help_text="Conservé même si l'utilisateur n'existe pas, pour détecter les tentatives suspectes")
    adresse_ip = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    succes = models.BooleanField()
    date_tentative = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'journal_connexions'
        ordering = ['-date_tentative']
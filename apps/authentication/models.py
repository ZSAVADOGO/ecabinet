import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class UserRole(models.TextChoices):
        ASSOCIE = 'associe', 'Associé'
        AVOCAT = 'avocat', 'Avocat'
        COLLABORATEUR = 'collaborateur', 'Collaborateur'
        SECRETARIAT = 'secretariat', 'Secrétariat'
        STAGIAIRE = 'stagiaire', 'Stagiaire'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    #email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.COLLABORATEUR,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Django utilise l'email pour l'authentification si souhaité, sinon username par défaut
    #REQUIRED_FIELDS = ['email', 'nom', 'prenom']
    nom = models.CharField(max_length=255, db_index=True)
    prenom = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(null=True, blank=True)


    class Meta:
        db_table = 'users'

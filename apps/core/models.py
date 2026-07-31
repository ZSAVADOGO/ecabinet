# apps/core/models.py
import uuid
from django.conf import settings
from django.db import models


class PermissionRole(models.Model):
    """
    Surcharge d'une capacité pour TOUT un rôle (ex: autoriser tous les stagiaires
    à modifier un dossier). Vient s'ajouter/retirer par rapport à la valeur par
    défaut définie dans apps.core.permissions.CAPACITES.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, db_index=True)  # valeurs alignées sur User.UserRole
    capacite = models.CharField(max_length=50, db_index=True)  # valeurs alignées sur CAPACITES.keys()
    autorise = models.BooleanField(help_text="Coché = accorde l'accès. Décoché = retire l'accès, même si accordé par défaut.")
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permissions_roles'
        unique_together = ('role', 'capacite')
        verbose_name = "Surcharge de permission (par rôle)"
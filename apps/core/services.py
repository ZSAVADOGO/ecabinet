# apps/core/services.py
from django.core.exceptions import ValidationError
from apps.core.permissions import CAPACITES, CAPACITES_VERROUILLEES_POUR_ASSOCIE
from apps.core.models import PermissionRole


""" def definir_permission_role(role: str, capacite: str, autorise: bool, utilisateur_qui_modifie) -> PermissionRole:
    if capacite not in CAPACITES:
        raise ValidationError(f"Capacité inconnue : '{capacite}'.")

    surcharge, _ = PermissionRole.objects.update_or_create(
        role=role, capacite=capacite,
        defaults={"autorise": autorise, "modifie_par": utilisateur_qui_modifie},
    )
    return surcharge """

# apps/core/services.py — definir_permission_role
def definir_permission_role(role, capacite, autorise, utilisateur_qui_modifie):
    if capacite not in CAPACITES:
        raise ValidationError(f"Capacité inconnue : '{capacite}'.")

    if role == 'associe' and capacite in CAPACITES_VERROUILLEES_POUR_ASSOCIE and not autorise:
        raise ValidationError("Cette capacité ne peut pas être retirée au rôle Associé (protection anti-blocage du système).")

    surcharge, _ = PermissionRole.objects.update_or_create(
        role=role, capacite=capacite,
        defaults={"autorise": autorise, "modifie_par": utilisateur_qui_modifie},
    )
    return surcharge


def reinitialiser_permission_role(role: str, capacite: str):
    """Supprime la surcharge : le rôle retombe sur la valeur par défaut du code."""
    PermissionRole.objects.filter(role=role, capacite=capacite).delete()
# apps/core/services.py
from django.core.exceptions import ValidationError
from apps.core.permissions import CAPACITES, CAPACITES_VERROUILLEES_POUR_ASSOCIE
from apps.core.models import PermissionRole

import requests
from django.utils import timezone
from notifications.models import SMSGroupEnvoi, SMSDetailDestinataire
from notifications.services import recalculer_statut_groupe  # Importer votre helper ici
import logging
logger = logging.getLogger(__name__)

""" def definir_permission_role(role: str, capacite: str, autorise: bool, utilisateur_qui_modifie) -> PermissionRole:
    if capacite not in CAPACITES:
        raise ValidationError(f"Capacité inconnue : '{capacite}'.")

    surcharge, _ = PermissionRole.objects.update_or_create(
        role=role, capacite=capacite,
        defaults={"autorise": autorise, "modifie_par": utilisateur_qui_modifie},
    )
    return surcharge """


class AQILASSMSService:

    @staticmethod
    def sync_delivery_status(groupe: SMSGroupEnvoi):
        """
        Interroge l'API Aqilas avec GET /sms/{bulk_id} et met à jour
        les destinataires et le groupe de manière optimisée en masse (Bulk Update).
        """
        if not groupe.bulk_id:
            return

        base_url = groupe.provider.base_url.rstrip('/')
        url = f"{base_url}/sms/{groupe.bulk_id}"
        api_token = groupe.provider.api_key.strip() if groupe.provider.api_key else ""

        headers = {
            "X-AUTH-TOKEN": api_token,
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            # Gérer le cas où le bulk_id n'existe pas ou est introuvable sur l'API
            if response.status_code == 404:
                logger.warning(f"Bulk ID {groupe.bulk_id} introuvable sur Aqilas.")
                return

            response.raise_for_status()
            donnees_api = response.json()  # C'est une LISTE d'objets JSON

            if not isinstance(donnees_api, list):
                logger.error(f"Format de réponse inattendu pour {groupe.bulk_id} : {donnees_api}")
                return

            # 1. Charger tous les destinataires du groupe en 1 seule requête SQL
            destinataires_dict = {
                dest.telephone: dest 
                for dest in groupe.details.all()
            }

            destinataires_a_mettre_a_jour = []
            
            # 2. Mapper les réponses de l'API avec nos objets en mémoire
            for item in donnees_api:
                phone = item.get("to")
                statut_api = item.get("status")
                sms_id_api = item.get("id")

                if phone in destinataires_dict:
                    destinataire = destinataires_dict[phone]
                    changement = False

                    # Mettre à jour l'ID SMS individuel si non encore renseigné
                    if sms_id_api and destinataire.sms_provider_id != sms_id_api:
                        destinataire.sms_provider_id = sms_id_api
                        changement = True

                    # Mettre à jour le statut s'il a évolué
                    if statut_api and destinataire.status != statut_api:
                        destinataire.status = statut_api
                        destinataire.updated_at = timezone.now()
                        changement = True

                    if changement:
                        destinataires_a_mettre_a_jour.append(destinataire)

            # 3. Optimisation Majeure : Écriture SQL massive (bulk_update)
            if destinataires_a_mettre_a_jour:
                SMSDetailDestinataire.objects.bulk_update(
                    destinataires_a_mettre_a_jour,
                    fields=["sms_provider_id", "status", "updated_at"],
                    batch_size=500  # Traite par paquets de 500 pour économiser la mémoire
                )

                # 4. Recalculer le statut global du groupe parent
                recalculer_statut_groupe(groupe)
                logger.info(f"Synchronisation réussie pour le groupe {groupe.id} ({len(destinataires_a_mettre_a_jour)} mis à jour).")

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau/API lors de la synchro du groupe {groupe.id}: {str(e)}")

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
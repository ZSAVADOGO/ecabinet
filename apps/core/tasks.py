# notifications/tasks.py ou management/commands/sync_sms_status.py
import logging

from celery import shared_task
from notifications.models import SMSGroupEnvoi
from .services import AQILASSMSService

logger = logging.getLogger(__name__)

@shared_task
def update_pending_sms_statuses():
    # Ne synchroniser que les groupes qui ont encore des SMS en attente
    logger.info("🚀 DEBUT : Synchronisation des statuts SMS lancée par Celery Beat...")
    pending_bulks = SMSGroupEnvoi.objects.filter(
        statut__in=[SMSGroupEnvoi.StatutGlobal.ENVOYE, SMSGroupEnvoi.StatutGlobal.PARTIEL],
        bulk_id__isnull=False
    ).select_related('provider')

    for bulk in pending_bulks:
        AQILASSMSService.sync_delivery_status(bulk)
    logger.info("✅ FIN : Synchronisation terminée avec succès.")
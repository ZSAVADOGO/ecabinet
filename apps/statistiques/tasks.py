# notifications/tasks.py ou management/commands/sync_sms_status.py
from celery import shared_task
from .models import SMSGroupEnvoi
from .services import AQILASSMSService

@shared_task
def update_pending_sms_statuses():
    """
    Récupère tous les SMS en cours d'acheminement et interroge l'API du fournisseur
    """
    pending_bulks = SMSGroupEnvoi.objects.filter(
        statut__in=[SMSGroupEnvoi.StatutGlobal.ENVOYE, SMSGroupEnvoi.StatutGlobal.PARTIEL],
        bulk_id__isnull=False
    )
    
    for bulk in pending_bulks:
        AQILASSMSService.sync_delivery_status(bulk.bulk_id)
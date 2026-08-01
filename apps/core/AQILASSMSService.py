import requests
from django.utils import timezone
from .models import SMSGroupEnvoi, SMSDetailDestinataire
from .utils import recalculer_statut_groupe  # Importer votre helper ici
import logging
logger = logging.getLogger(__name__)


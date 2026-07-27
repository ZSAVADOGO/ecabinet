import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ProviderSMS(models.Model):
    """
    Gestion dynamique des Gateways / API SMS (AQILAS, Orange, Moov, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True, help_text="Ex: AQILAS SMS, Orange BF")
    sender_id = models.CharField(max_length=11, default="CABINET", help_text="Nom de l'expéditeur affiché (ex: AQILAS)")
    base_url = models.URLField(help_text="Ex: https://api.aqilas.com/v1")
    api_key = models.CharField(max_length=255, help_text="Clé d'API ou Token d'authentification")
    
    is_default = models.BooleanField(default=False, help_text="Définir comme fournisseur par défaut")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sms_providers'
        verbose_name = "Fournisseur SMS API"
        verbose_name_plural = "Fournisseurs SMS API"

    def save(self, *args, **kwargs):
        # S'assurer qu'un seul fournisseur est défini 'par défaut'
        if self.is_default:
            ProviderSMS.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        default_str = " (Par défaut)" if self.is_default else ""
        return f"{self.nom}{default_str}"


class SMSGroupEnvoi(models.Model):
    """
    Représente une campagne ou un envoi groupé de SMS (Bulk)
    """
    class StatutGlobal(models.TextChoices):
        EN_ATTENTE = 'PENDING', 'En attente'
        ENVOYE = 'SENT', 'Envoyé au Provider'
        PARTIEL = 'PARTIAL', 'Partiellement Livré'
        TERMINE = 'DELIVERED', 'Tous Livrés'
        ECHEC = 'FAILED', 'Échec Envoi'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(ProviderSMS, on_delete=models.PROTECT, related_name='envois')
    
    # Rapprochement optionnel avec l'Agenda (Lien faible pour conserver la modularité)
    evenement_agenda = models.ForeignKey(
        'agenda.EvenementAgenda', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='campagnes_sms'
    )

    # Rapprochement optionnel avec Dossier (Lien faible pour conserver la modularité)
    dossier = models.ForeignKey('dossier.Dossier', null=True, blank=True, on_delete=models.SET_NULL, related_name='campagnes_sms')
    
    expediteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    message_text = models.TextField()
    bulk_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="ID retourné par l'API SMS")
    
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Coût total en XOF")
    currency = models.CharField(max_length=10, default="XOF")
    
    statut = models.CharField(max_length=20, choices=StatutGlobal.choices, default=StatutGlobal.EN_ATTENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    send_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'sms_group_envois'
        ordering = ['-created_at']

    def __str__(self):
        return f"Bulk SMS {self.bulk_id or self.id} - {self.get_statut_display()}"


class SMSDetailDestinataire(models.Model):
    """
    Traçabilité individuelle par numéro de téléphone dans le Bulk
    """
    class StatutSMS(models.TextChoices):
        PENDING = 'PENDING', 'En cours d\'acheminement'
        DELIVERY_SUCCESS = 'DELIVERY_SUCCESS', 'Reçu par le destinataire'
        DELIVERY_FAILED = 'DELIVERY_FAILED', 'Échec de livraison'
        EXPIRED = 'EXPIRED', 'Expiré'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group_envoi = models.ForeignKey(SMSGroupEnvoi, on_delete=models.CASCADE, related_name='details')
    
    # ID individuel renvoyé par le GET /sms/{bulk_id}
    sms_provider_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    telephone = models.CharField(max_length=30, db_index=True)
    expediteur = models.CharField(max_length=30, db_index=True)
    destinataire_nom = models.CharField(max_length=30, db_index=True)
    destinataire_role = models.CharField(max_length=30, db_index=True)
    
    partie_prenante = models.ForeignKey('agenda.PartiePrenante', null=True, blank=True, on_delete=models.SET_NULL)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    
    status = models.CharField(max_length=30, choices=StatutSMS.choices, default=StatutSMS.PENDING, db_index=True)
    
    send_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sms_detail_destinataires'

    def __str__(self):
        return f"{self.telephone} : {self.status}"
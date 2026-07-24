# agenda/services_notification.py
from django.core.mail import send_mail
from django.conf import settings


def notifier_evenement(evenement, canal='email'):
    """
    canal : 'email', 'sms', ou 'les_deux'
    Envoie un rappel à chaque partie prenante notifiable rattachée à l'événement.
    """
    resultats = []
    for partie in evenement.destinataires.filter(notifiable=True):
        message = (
            f"Rappel : {evenement.titre} le {evenement.date_heure.strftime('%d/%m/%Y à %H:%M')} "
            f"— Dossier {evenement.dossier.reference if evenement.dossier else ''}"
        )
        if canal in ('email', 'les_deux') and partie.email:
            send_mail(
                subject=f"[eCabinet] {evenement.titre}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[partie.email],
            )
            resultats.append({"partie": partie.nom, "canal": "email", "statut": "envoyé"})
        if canal in ('sms', 'les_deux') and partie.telephone:
            _envoyer_sms(partie.telephone, message)  # cf. note ci-dessous
            resultats.append({"partie": partie.nom, "canal": "sms", "statut": "envoyé"})
    return resultats


def _envoyer_sms(numero, message):
    """
    L'envoi de SMS nécessite un fournisseur tiers (Twilio, Orange SMS API, etc.) —
    Django n'a pas d'équivalent natif à send_mail() pour le SMS.
    """
    raise NotImplementedError("Brancher ici l'API du fournisseur SMS choisi (ex: Twilio, Orange Burkina API).")
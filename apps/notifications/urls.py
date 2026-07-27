from django.urls import path
from django.http import HttpResponse

from . import views


app_name = 'notifications'


urlpatterns = [
    path("", views.notification_dashboard, name="liste"),
    path("api/liste/", views.api_lister_sms, name="api_lister_sms"),
    path("api/creer/", views.api_creer_sms, name="api_creer_sms"),
    path("api/<uuid:sms_id>/", views.api_detail_sms, name="api_detail_sms"),
    path("api/<uuid:sms_id>/modifier/", views.api_modifier_sms, name="api_modifier_sms"),

    path("api/fournisseurs/", views.api_lister_fournisseurs, name="api_lister_fournisseurs"),
    path("api/fournisseurs/creer/", views.api_creer_fournisseur, name="api_creer_fournisseur"),
    path("api/fournisseurs/<uuid:fournisseur_id>/modifier/", views.api_modifier_fournisseur, name="api_modifier_fournisseur"),
    path("api/fournisseurs/<uuid:fournisseur_id>/supprimer/", views.api_supprimer_fournisseur, name="api_supprimer_fournisseur"),
]

""" urlpatterns = [
    #path('', lambda request: HttpResponse('Page Liste des notifications...'), name='liste'),
    path("", views.notification_dashboard, name="liste"),
    path("creer/notification/", views.notification_creation_wizard, name="notification_creation_wizard"),
    path("programmer/notification/", views.notification_programmer, name="notification_programmer"),
    path("api/<uuid:notification_id>/", views.api_detail_notification, name="api_detail_notification"),
    path("api/<uuid:notification_id>/supprimer/", views.api_supprimer_notification, name="api_supprimer_notification"),
    path("api/<uuid:notification_id>/modifier/", views.api_modifier_notification, name="api_modifier_notification"),

    # Page principale du module notification, accessible via /notifications/
    
] """

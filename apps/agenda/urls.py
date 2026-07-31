# agenda/urls.py
from django.urls import path

from agenda import views

app_name = "agenda"

urlpatterns = [
    path("", views.agenda_dashboard, name="liste"),
    path("api/liste/", views.api_lister_evenements, name="api_lister_evenements"),
    path("api/creer/", views.api_creer_evenement, name="api_creer_evenement"),
    path("api/<uuid:evenement_id>/", views.api_detail_evenement, name="api_detail_evenement"),
    path("api/<uuid:evenement_id>/modifier/", views.api_modifier_evenement_agenda, name="api_modifier_evenement"),
    path("api/<uuid:evenement_id>/supprimer/", views.api_supprimer_evenement, name="api_supprimer_evenement"),

    path("api/dossiers/<uuid:dossier_id>/parties-prenantes/", views.api_parties_prenantes_dossier, name="charger_parties_prenantes_dossier"),
    path("api/parties-prenantes/creer/", views.api_creer_partie_prenante_rapide, name="api_creer_partie_prenante_rapide"),
    path("api/parties-prenantes/<uuid:pk>/supprimer/", views.api_supprimer_partie_prenante_rapide, name="api_supprimer_partie_prenante_rapide"),

    path("api/dossiers/<uuid:dossier_id>/responsables/", views.charger_responsables_dossier, name="charger_responsables_dossier"),

# NOUVELLE ROUTE : Obtention de la juridiction (Tribunal & Chambre)
    #path("api/dossiers/<uuid:dossier_id>/juridiction/", views.charger_juridiction_evenement_ou_dossier, name="api_obtenir_juridiction"),
    path("api/juridiction/", views.charger_juridiction_evenement_ou_dossier, name="api_obtenir_juridiction"),

    #path('api/dossiers/<uuid:dossier_id>/juridiction/', views.charger_juridiction_evenement_ou_dossier, name='api_charger_juridiction'),
    #path("api/dossier/<uuid:dossier_id>/", views.api_agenda_par_dossier, name="api_par_dossier"),
]


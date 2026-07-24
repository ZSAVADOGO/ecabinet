# agenda/urls.py
from django.urls import path

from agenda import views

app_name = "agenda"

urlpatterns = [
    path("", views.agenda_dashboard, name="liste"),
    path("api/liste/", views.api_lister_evenements, name="api_lister_evenements"),
    path("api/creer/", views.api_creer_evenement, name="api_creer_evenement"),
    path("api/<uuid:evenement_id>/", views.api_detail_evenement, name="api_detail_evenement"),
    path("api/<uuid:evenement_id>/modifier/", views.api_modifier_evenement, name="api_modifier_evenement"),
    path("api/<uuid:evenement_id>/supprimer/", views.api_supprimer_evenement, name="api_supprimer_evenement"),

# CORRECTION : Remplacer "views.charger_parties_prenantes_dossier" par "views.api_parties_prenantes_dossier"
    path("api/dossiers/<uuid:dossier_id>/parties-prenantes/", views.api_parties_prenantes_dossier, name="charger_parties_prenantes_dossier"),
    path("api/parties-prenantes/creer/", views.api_creer_partie_prenante_rapide, name="api_creer_partie_prenante_rapide"),
    path("api/parties-prenantes/<uuid:pk>/supprimer/", views.api_supprimer_partie_prenante_rapide, name="api_supprimer_partie_prenante_rapide"),

]


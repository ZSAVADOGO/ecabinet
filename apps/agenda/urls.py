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
]
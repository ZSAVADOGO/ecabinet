# authentication/urls.py
from django.urls import path
from . import views


app_name = "authentication"

urlpatterns = [
    path("", views.utilisateur_dashboard, name="liste"),
    path("api/", views.api_lister_utilisateurs, name="api_lister_utilisateurs"),
    path("api/creer/", views.api_creer_utilisateur, name="api_creer_utilisateur"),
    path("api/<uuid:utilisateur_id>/", views.api_detail_utilisateur, name="api_detail_utilisateur"),
    path("api/<uuid:utilisateur_id>/modifier/", views.api_modifier_utilisateur, name="api_modifier_utilisateur"),
    path("api/<uuid:utilisateur_id>/supprimer/", views.api_supprimer_utilisateur, name="api_supprimer_utilisateur"),
]


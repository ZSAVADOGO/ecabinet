from django.urls import path
from django.http import HttpResponse

from . import views


app_name = 'dossier'

urlpatterns = [
    #path('', lambda request: HttpResponse('Page Liste des Dossiers...'), name='liste'),
    path("", views.dossier_dashboard, name="liste"),
    #path("dossiers/", views.dossier_dashboard, name="dossier_dashboard"),
    path("api/liste/", views.api_lister_dossiers, name="api_lister_dossiers"),
    path("api/creer/", views.api_creer_dossier, name="api_creer_dossier"),
    path("api/<uuid:dossier_id>/", views.api_detail_dossier, name="api_detail_dossier"),
    path("api/<uuid:dossier_id>/modifier/", views.api_modifier_dossier, name="api_modifier_dossier"),
    path("api/<uuid:dossier_id>/supprimer/", views.api_supprimer_dossier, name="api_supprimer_dossier"),
    # Page principale du module Dossier, accessible via /dossiers/
    
]

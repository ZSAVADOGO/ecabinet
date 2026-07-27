from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.page_accueil, name='index'),
    #path('', views.page_accueil, name='liste'),

    # dashboard/urls.py — ajouts
    path("api/stats/dossiers/", views.api_stats_dossiers, name="api_stats_dossiers"),
    path("api/stats/agenda/", views.api_stats_agenda, name="api_stats_agenda"),


]

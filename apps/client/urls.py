from django.urls import path
from django.http import HttpResponse

from . import views


app_name = 'client'

urlpatterns = [
    #path('', lambda request: HttpResponse('Page Liste des Clients...'), name='liste'),
    path("", views.client_dashboard, name="liste"),
    
            # Endpoints de l'API AJAX (accessibles via /clients/api/liste/, etc.)
    path("api/liste/", views.api_lister_clients, name="api_lister_clients"),
    path("api/creer/", views.api_creer_client, name="api_creer_client"),
    path("api/<uuid:client_id>/", views.api_detail_client, name="api_detail_client"),
    path("api/<uuid:client_id>/modifier/", views.api_modifier_client, name="api_modifier_client"),
    path("api/<uuid:client_id>/supprimer/", views.api_supprimer_client, name="api_supprimer_client"),

]

# facturation/urls.py
from django.urls import path

from facturation import views

app_name = "facturation"

urlpatterns = [ 
    path("", views.facturation_dashboard, name="liste"),
    path("api/liste/", views.api_lister_factures, name="api_lister_factures"),
    path("api/creer/", views.api_creer_facture, name="api_creer_facture"),
    path("api/<uuid:facture_id>/", views.api_detail_facture, name="api_detail_facture"),
    path("api/<uuid:facture_id>/modifier/", views.api_modifier_facture, name="api_modifier_facture"),
    path("api/<uuid:facture_id>/supprimer/", views.api_supprimer_facture, name="api_supprimer_facture"),
]
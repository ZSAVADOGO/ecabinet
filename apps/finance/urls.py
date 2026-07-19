# facturation/urls.py
from django.urls import path

from facturation import views

app_name = "facturation"

urlpatterns = [
    path("facturation/", views.finance_dashboard, name="index"),
    path("facturation/api/tableau-bord/", views.api_tableau_bord_finance, name="api_tableau_bord"),
]
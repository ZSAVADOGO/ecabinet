from django.urls import path
from . import views

app_name = 'statistiques'

urlpatterns = [
    path("", views.statistiques_dashboard, name="liste"),
]
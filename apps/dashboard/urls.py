from django.urls import path
from dashboard import controllers

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.page_accueil, name='index'),
    path('api/metrics/', views.api_metrics_graphiques, name='api_metrics'),


]

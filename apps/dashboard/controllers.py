from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from dashboard.services import DashboardMetricsService

def page_accueil(request):
    """ Rend la page HTML d'accueil vide instantanément """
    return render(request, 'dashboard/index.html')

@api_view(['GET'])
def api_metrics_graphiques(request):
    """ Endpoint API asynchrone ultra-rapide pour alimenter Chart.js """
    donnees = DashboardMetricsService.obtenir_donnees_graphiques()
    return Response(donnees)

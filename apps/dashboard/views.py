from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from dashboard.services import DashboardMetricsService

def page_accueil(request):
    """
    Rend le squelette HTML de la page d'accueil instantanément (Lazy Loading).
    """
    return render(request, 'dashboard/index.html')

@api_view(['GET'])
def api_metrics_graphiques(request):
    """
    Endpoint API asynchrone appelé par Chart.js pour dessiner les camemberts.
    Renvoie uniquement des données numériques agrégées très légères.
    """
    donnees = DashboardMetricsService.obtenir_donnees_graphiques()
    return Response(donnees)

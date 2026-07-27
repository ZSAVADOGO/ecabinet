from django.shortcuts import render

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from dashboard.services import stats_dossiers_par_statut, stats_dossiers_par_avocat, stats_agenda, annees_disponibles_agenda

from dossier.models import Dossier
from agenda.models import EvenementAgenda


""" def index(request):
    contexte = {
        "stats_dossiers_initial": stats_dossiers_par_statut(),
        "stats_agenda_initial": stats_agenda_par_periode('mois'),
        "total_dossiers": Dossier.objects.count(),
        "total_agenda": EvenementAgenda.objects.count(),
    }
    return render(request, "dashboard/index.html", contexte) """

# dashboard/views.py — accepter page/page_size
# dashboard/views.py
@require_GET
def api_stats_dossiers(request):
    groupe = request.GET.get('groupe', 'statut')
    page = int(request.GET.get('page', 1))
    if groupe == 'avocat':
        return JsonResponse(stats_dossiers_par_avocat(page=page))
    return JsonResponse(stats_dossiers_par_statut())


@require_GET
def api_stats_agenda(request):
    vue = request.GET.get('vue', 'mois')
    annee = request.GET.get('annee')
    page = int(request.GET.get('page', 1))
    return JsonResponse(stats_agenda(vue=vue, annee=int(annee) if annee else None, page=page))


def page_accueil(request):
    contexte = {
        "stats_dossiers_initial": stats_dossiers_par_statut(),
        "stats_agenda_initial": stats_agenda(vue='mois'),
        "total_dossiers": Dossier.objects.count(),
        "total_agenda": EvenementAgenda.objects.count(),
        "annees_disponibles": annees_disponibles_agenda(),
    }
    return render(request, "dashboard/index.html", contexte)


""" @require_GET
def api_stats_dossiers(request):
    groupe = request.GET.get('groupe', 'statut')
    if groupe == 'avocat':
        return JsonResponse(stats_dossiers_par_avocat())
    return JsonResponse(stats_dossiers_par_statut())


@require_GET
def api_stats_agenda(request):
    periode = request.GET.get('periode', 'mois')
    return JsonResponse(stats_agenda_par_periode(periode)) """



""" def page_accueil(request):
    return render(request, 'dashboard/index.html')

@api_view(['GET'])
def api_metrics_graphiques(request):
    donnees = DashboardMetricsService.obtenir_donnees_graphiques()
    return Response(donnees) """



from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.core.permissions import peut
from statistiques.services import kpis_juridiques, kpis_secretariat, kpis_comptable


def statistiques_dashboard(request):
    date_debut = request.GET.get('date_debut') or None
    date_fin = request.GET.get('date_fin') or None

    contexte = {'date_debut': date_debut or '', 'date_fin': date_fin or ''}
    acces_accorde = False

    if peut(request.user, 'voir_statistiques_juridiques'):
        contexte['juridique'] = kpis_juridiques(date_debut, date_fin)
        acces_accorde = True
    if peut(request.user, 'voir_statistiques_secretariat'):
        contexte['secretariat'] = kpis_secretariat(date_debut, date_fin)
        acces_accorde = True
    if peut(request.user, 'voir_statistiques_comptable'):
        contexte['comptable'] = kpis_comptable(date_debut, date_fin)
        acces_accorde = True

    if not acces_accorde:
        raise PermissionDenied("Vous n'avez accès à aucune statistique.")

    return render(request, "statistiques/statistiques_dashboard.html", contexte)

""" @login_required
def statistiques_dashboard(request):
    
    contexte = {}
    acces_accorde = False

    if peut(request.user, 'voir_statistiques_juridiques'):
        contexte['juridique'] = kpis_juridiques()
        acces_accorde = True
    if peut(request.user, 'voir_statistiques_secretariat'):
        contexte['secretariat'] = kpis_secretariat()
        acces_accorde = True
    if peut(request.user, 'voir_statistiques_comptable'):
        contexte['comptable'] = kpis_comptable()
        acces_accorde = True

    date_debut = request.GET.get('date_debut') or None
    date_fin = request.GET.get('date_fin') or None
    print(f"DEBUG FILTRE >>> date_debut={date_debut}, date_fin={date_fin}")


    if not acces_accorde:
        raise PermissionDenied("Vous n'avez accès à aucune statistique.")

    return render(request, "statistiques/statistiques_dashboard.html", contexte) """
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from apps.core.permissions import peut
from statistiques.services import kpis_juridiques, kpis_secretariat, kpis_comptable


@login_required
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

    if not acces_accorde:
        raise PermissionDenied("Vous n'avez accès à aucune statistique.")

    return render(request, "statistiques/statistiques_dashboard.html", contexte)
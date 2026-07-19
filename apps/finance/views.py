# facturation/views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from facturation.services import options_clients

#from facturation.services import finance_service

from facturation.services import _queryset_periode, obtenir_tableau_bord



#@login_required
def finance_dashboard(request):
    #contexte = {"clients": facturation_service.options_clients()}
    contexte = {"clients": options_clients()}
    return render(request, "facturation/finance_dashboard.html", contexte)


#@login_required
@require_GET
def api_tableau_bord_finance(request):
    resultat = obtenir_tableau_bord(
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        client_id=request.GET.get("client_id", ""),
    )
    return JsonResponse(resultat, status=200)
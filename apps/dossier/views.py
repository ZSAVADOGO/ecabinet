# dossier/views.py
"""
Contrôleur (vues) du module Dossier.
"""

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db import transaction  # Résout "transaction" is not defined

from django.utils import timezone

from dossier.models import Dossier
from agenda.models import EvenementAgenda
from facturation.models import Facture

from dossier.services import (creer_facture_pour_dossier, creer_agenda_pour_dossier, dossier_vers_dict, lister_dossiers, obtenir_dossier, 
creer_dossier, modifier_dossier, supprimer_dossier, options_clients, options_avocats)

from client.models import Client
from apps.authentication.models import Tribunal

from django.contrib.auth import get_user_model # <-- Ajouté pour récupérer le modèle User

User = get_user_model()


def dossier_creation_wizard(request):
    annee_actuelle = timezone.now().strftime("%Y")
    prefixe = f"DOS-{annee_actuelle}-"
    
    # On regarde le dernier dossier de l'année sans bloquer la séquence
    dernier_dossier = Dossier.objects.filter(reference__startswith=prefixe).order_by('-reference').first()
    if dernier_dossier:
        try:
            dernier_compteur = int(dernier_dossier.reference.split('-')[-1])
            prochain_compteur = dernier_compteur + 1
        except (ValueError, IndexError):
            prochain_compteur = 1
    else:
        prochain_compteur = 1
        
    # On génère une valeur indicative pour l'UI
    prochaine_ref_estimative = f"{prefixe}{prochain_compteur:04d}"

    contexte = {
        "clients": Client.objects.all().order_by('nom', 'raison_sociale'),
        "tribunaux": Tribunal.objects.all().order_by('ville', 'nom'),
        "statut_facture": Facture.StatutFacture.choices,
        "types_agenda": EvenementAgenda.TypeEvenement.choices,
        "statut_dossier": Dossier.StatutDossier.choices,
        "type_affaire": Dossier.TypeAffaire.choices,
        "avocats": User.objects.filter(role__in=["associe", "avocat"]).order_by("first_name"),
        
        # ON PASSE LA VALEUR ESTIMÉE AU TEMPLATE
        "prochaine_reference": prochaine_ref_estimative, 
    }
    return render(request, "dossier/ajout_dossier.html", contexte)

""" def dossier_creation_wizard(request):
    # Cette vue se contente d'afficher le fichier HTML du formulaire multi-pages
    contexte = {
        "clients": Client.objects.all().order_by('nom', 'raison_sociale'),
        "tribunaux": Tribunal.objects.all().order_by('ville', 'nom'),
        "statut_facture": Facture.StatutFacture.choices,
        
        # CORRECTION ICI : Appel des choix de type d'événement du modèle
        "types_agenda": EvenementAgenda.TypeEvenement.choices,
        
        "statut_dossier": Dossier.StatutDossier.choices,
        "type_affaire": Dossier.TypeAffaire.choices,
        "avocats": User.objects.filter(role__in=["associe", "avocat"]).order_by("first_name"),
    }
    return render(request, "dossier/ajout_dossier.html", contexte) """


##@login_required
def dossier_dashboard(request):
    """Rend le template unique du dashboard Dossier (tableau + modals intégrés)."""
    contexte = {
        "statuts_dossier": Dossier.StatutDossier.choices,
        "types_affaire": Dossier.TypeAffaire.choices,
        "clients": options_clients(),
        "avocats": options_avocats(),
    }
    return render(request, "dossier/dossier_dashboard.html", contexte)


##@login_required
@require_GET
def api_lister_dossiers(request):
    """
    Query params : q, statut, type_affaire, client_id, date_debut, date_fin, page, page_size
    """
    resultat = lister_dossiers(
        recherche=request.GET.get("q", "").strip(),
        statut=request.GET.get("statut", ""),
        type_affaire=request.GET.get("type_affaire", ""),
        client_id=request.GET.get("client_id", ""),
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
    )
    return JsonResponse(resultat, status=200)


##@login_required
@require_GET
def api_detail_dossier(request, dossier_id):
    try:
        dossier = obtenir_dossier(dossier_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Dossier introuvable."}, status=404)
    return JsonResponse(dossier_vers_dict(dossier), status=200)


##@login_required
""" @require_http_methods(["POST"])
@transaction.atomic
def api_creer_dossier(request):
    print("le request --> ",request)

    user_pour_test = request.user
    if not user_pour_test.is_authenticated:
        user_pour_test = User.objects.first()
        if not user_pour_test:
                user_pour_test = User.objects.create_user(
                    username="testuser", 
                    email="test@example.com", 
                    password="password123"
                )

    try:
        data = json.loads(request.body)
        if 'dossier' not in data:
            return JsonResponse({"erreur": "Le bloc de données 'dossier' est obligatoire."}, status=400)

        dossier = creer_dossier(data['dossier'], user_pour_test)

        print("le dossier --> ",dossier)

        facture = None
        if 'facture' in data:
            facture = creer_facture_pour_dossier(dossier, data['facture'], user_pour_test)

        agenda = None
        if 'agenda' in data:
            agenda = creer_agenda_pour_dossier(dossier, data['agenda'], user_pour_test)

        print("le dossier --> ",dossier, "la facture --> ",facture, "l'agenda --> ",agenda)

    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)
    except KeyError as ke:
        return JsonResponse({"erreur": f"Le paramètre obligatoire suivant est manquant : {ke}"}, status=400)

    dossier.refresh_from_db()

    reponse = {"message": "Dossier créé avec succès.", "dossier": dossier_vers_dict(dossier)}
    if facture:
        reponse["facture"] = {"numero": facture.numero, "montant_ttc": str(facture.montant_ttc)}
    if agenda:
        reponse["agenda"] = {"titre": agenda.titre, "date_heure": agenda.date_heure.isoformat()}

    return JsonResponse(reponse, status=201) """


@require_http_methods(["POST"])
def api_creer_dossier(request):
    print("le request --> ", request)

    # 🛠️ DÉSACTIVATION DE LA SÉCURITÉ POUR LES TESTS
    user_pour_test = request.user
    if not user_pour_test.is_authenticated:
        user_pour_test = User.objects.first()
        if not user_pour_test:
            user_pour_test = User.objects.create_user(
                username="testuser", 
                email="test@example.com", 
                password="password123"
            )

    try:
        # L'utilisation du gestionnaire de contexte garantit le "Tout ou Rien"
        # sur l'ensemble des services appelés à l'intérieur.
        with transaction.atomic():
            data = json.loads(request.body)
            
            if 'dossier' not in data:
                return JsonResponse({"erreur": "Le bloc de données 'dossier' est obligatoire."}, status=400)

            # 1. Appel du service de création du Dossier
            dossier = creer_dossier(data['dossier'], user_pour_test)
            print("le dossier créé via service --> ", dossier)
            summary = f"<b>📂 Dossier créé :</b> Réf: {dossier.reference} — {dossier.intitule}"

            # 2. Appel conditionnel du service de Facturation
            facture = None
            if 'facture' in data:
                facture = creer_facture_pour_dossier(dossier, data['facture'], user_pour_test)
                summary += f"<br><b>💳 Facture générée :</b> N° {facture.numero} ({facture.montant_ttc} F CFA TTC)"
            # 3. Appel conditionnel du service d'Agenda
            agenda = None
            if 'agenda' in data:
                agenda = creer_agenda_pour_dossier(dossier, data['agenda'], user_pour_test)
                icone_alerte = "🚨 " if agenda.critique else "📅 "
                date_formatee = agenda.date_heure.strftime('%d/%m/%Y à %H:%M')
                summary += f"<br><b>{icone_alerte}Agenda programmé :</b> {agenda.titre} (le {date_formatee})"

            print("Bilan des services -> Dossier:", dossier, "Facture:", facture, "Agenda:", agenda)

            # 🛠️ FIX ATTRIBUTEERROR 'STR' : On force le rafraîchissement de l'instance
            # avant la sérialisation pour convertir les chaînes de dates en objets 'date' Python.
            dossier.refresh_from_db()

            # Préparation de la réponse unifiée de succès
            reponse = {
                "message": "Dossier créé avec succès.", 
                "dossier": dossier_vers_dict(dossier),
                "redirect": "/dossiers/"
            }
            if facture:
                reponse["facture"] = {"numero": facture.numero, "montant_ttc": str(facture.montant_ttc)}
            if agenda:
                reponse["agenda"] = {"titre": agenda.titre, "date_heure": agenda.date_heure.isoformat()}

            return JsonResponse(reponse, status=201)

    except ValidationError as exc:
        print(f"⚠️ Erreur de validation levée par un service : {str(exc)}")
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
        
    except json.JSONDecodeError:
        print("⚠️ Erreur : JSON malformé fourni par le frontend")
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)
        
    except KeyError as ke:
        print(f"⚠️ Erreur de paramètre manquant dans le dictionnaire : {str(ke)}")
        return JsonResponse({"erreur": f"Le paramètre obligatoire suivant est manquant : {ke}"}, status=400)
        
    except Exception as e:
        print(f"⚠️ Erreur applicative générale (Rollback global opéré) : {str(e)}")
        return JsonResponse({"erreur": f"Échec de l'enregistrement global : {str(e)}"}, status=400)
    

""" @require_http_methods(["POST"])
def api_creer_dossier(request):
    try:
        payload = json.loads(request.body)
        dossier = creer_dossier(payload, request.user)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Dossier créé avec succès.", "dossier": dossier_vers_dict(dossier)},
        status=201,
    ) """



##@login_required
@require_http_methods(["POST"])
def api_modifier_dossier(request, dossier_id):
    # 🛠️ DÉSACTIVATION DE LA SÉCURITÉ POUR LES TESTS
    user_pour_test = request.user
    if not user_pour_test.is_authenticated:
        user_pour_test = User.objects.first()
            
    try:
        payload = json.loads(request.body)
        dossier = modifier_dossier(dossier_id, payload, user_pour_test)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Dossier introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Dossier modifié avec succès.", "dossier": dossier_vers_dict(dossier)},
        status=200,
    )


##@login_required
@require_http_methods(["POST"])
def api_supprimer_dossier(request, dossier_id):
    try:
        supprimer_dossier(dossier_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Dossier introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)

    return JsonResponse({"message": "Dossier supprimé avec succès."}, status=200)


# ---------------------------------------------------------------------------
# Export CSV / Excel — respecte les mêmes filtres que le tableau (q, statut,
# type_affaire, client_id, date_debut, date_fin), sans pagination.
# ---------------------------------------------------------------------------

def _filtres_export(request):
    return {
        "recherche": request.GET.get("q", "").strip(),
        "statut": request.GET.get("statut", ""),
        "type_affaire": request.GET.get("type_affaire", ""),
        "client_id": request.GET.get("client_id", ""),
        "date_debut": request.GET.get("date_debut", ""),
        "date_fin": request.GET.get("date_fin", ""),
    }


##@login_required
""" @require_GET
def api_exporter_dossiers_csv(request):
    contenu = exporter_dossiers_csv(**_filtres_export(request))
    reponse = HttpResponse(contenu, content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = 'attachment; filename="dossiers.csv"'
    return reponse """


##@login_required
""" @require_GET
def api_exporter_dossiers_excel(request):
    classeur = exporter_dossiers_excel(**_filtres_export(request))
    reponse = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    reponse["Content-Disposition"] = 'attachment; filename="dossiers.xlsx"'
    classeur.save(reponse)
    return reponse """


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)

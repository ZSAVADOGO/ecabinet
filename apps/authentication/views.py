# authentication/views.py
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

#from authentication.models import User, Specialite
#from apps.authentication.models import User, Specialite
from apps.authentication.models import User, Specialite

# On importe directement les fonctions autonomes du fichier services, comme pour client.
from apps.authentication.services import (
    obtenir_utilisateur,
    lister_utilisateurs,
    creer_utilisateur,
    modifier_utilisateur,
    supprimer_utilisateur,
    utilisateur_vers_dict,
)

from django.contrib.auth import get_user_model # <-- Ajouté pour récupérer le modèle User
User = get_user_model()


##@login_required
def utilisateur_dashboard(request):
    resultat = lister_utilisateurs(page=1, page_size=10)
    contexte = {
        "roles_utilisateur": User.UserRole.choices,
        "specialites_disponibles": Specialite.objects.all().order_by("libelle"),
        "resultats_initiaux": resultat["resultats"],
        "pagination_initiale": resultat["pagination"],
    }
    return render(request, "authentication/user_dashboard.html", contexte)


@require_GET
def api_lister_utilisateurs(request):
    resultat = lister_utilisateurs(
        recherche=request.GET.get("q", "").strip(),
        role=request.GET.get("role", ""),
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
        tri=request.GET.get("tri", "-created_at"),
    )
    return JsonResponse(resultat, status=200)


##@login_required
@require_GET
def api_detail_utilisateur(request, utilisateur_id):
    try:
        utilisateur = obtenir_utilisateur(utilisateur_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Utilisateur introuvable."}, status=404)
    return JsonResponse(utilisateur_vers_dict(utilisateur), status=200)


##@login_required
@require_POST
def api_creer_utilisateur(request):
    try:
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
        payload = json.loads(request.body)
        utilisateur = creer_utilisateur(payload, user_pour_test)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Utilisateur créé avec succès.", "utilisateur": utilisateur_vers_dict(utilisateur)},
        status=201,
    )


##@login_required
@require_http_methods(["POST"])
def api_modifier_utilisateur(request, utilisateur_id):
    try:
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
        payload = json.loads(request.body)
        utilisateur = modifier_utilisateur(utilisateur_id, payload, user_pour_test)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Utilisateur introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Utilisateur modifié avec succès.", "utilisateur": utilisateur_vers_dict(utilisateur)},
        status=200,
    )


##@login_required
@require_http_methods(["POST"])
def api_supprimer_utilisateur(request, utilisateur_id):
    try:
        supprimer_utilisateur(utilisateur_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Utilisateur introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)

    return JsonResponse({"message": "Utilisateur supprimé avec succès."}, status=200)


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
# authentication/views.py
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.core.permissions import CAPACITES, CAPACITES_VERROUILLEES_POUR_ASSOCIE

from apps.authentication.models import User, Specialite
from django.utils import timezone

#---- Securite
from django.contrib.auth.decorators import login_required
from .services import se_connecter, se_deconnecter
#----Fin securite

# On importe directement les fonctions autonomes du fichier services, comme pour client.
from apps.authentication.services import (
    obtenir_utilisateur,
    lister_utilisateurs,
    creer_utilisateur,
    modifier_utilisateur,
    supprimer_utilisateur,
    utilisateur_vers_dict,
)

from apps.core.decorators import capacite_requise
from apps.core.permissions import matrice_permissions


from django.contrib.auth import get_user_model # <-- Ajouté pour récupérer le modèle User
User = get_user_model()



# ----- Securite


""" @capacite_requise('gerer_utilisateurs')
def permissions_par_role_view(request):
    contexte = matrice_permissions()
    return render(request, "authentication/permissions_par_role.html", contexte) """
# authentication/views.py
@capacite_requise('gerer_utilisateurs')
def permissions_par_role_view(request):
    contexte = matrice_permissions()
    etat = {}
    for section in contexte['sections']:
        for ligne in section['lignes']:
            etat[ligne['cle']] = ligne['autorise_par_role']
    contexte['etat_permissions_json'] = etat
    contexte['capacites_verrouillees'] = list(CAPACITES_VERROUILLEES_POUR_ASSOCIE)
    return render(request, "authentication/permissions_par_role.html", contexte)


@require_http_methods(["GET", "POST"])
def connexion_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    erreur = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        mot_de_passe = request.POST.get("mot_de_passe", "")
        succes, message = se_connecter(request, email, mot_de_passe)
        if succes:
            if request.user.doit_changer_mot_de_passe:
                return redirect('authentication:changer_mot_de_passe_oblige')
            return redirect(request.GET.get('next') or 'dashboard:index')
        erreur = message

    return render(request, "authentication/connexion.html", {"erreur": erreur})


@login_required
def deconnexion_view(request):
    se_deconnecter(request)
    return redirect('authentication:connexion')


@login_required
@require_http_methods(["GET", "POST"])
def changer_mot_de_passe_oblige_view(request):
    """Bloque l'accès au reste de l'app tant que le mot de passe temporaire n'a pas été changé."""
    if not request.user.doit_changer_mot_de_passe:
        return redirect('dashboard:liste')

    erreur = None
    if request.method == "POST":
        nouveau = request.POST.get("nouveau_mot_de_passe", "")
        confirmation = request.POST.get("confirmation", "")
        if nouveau != confirmation:
            erreur = "Les deux mots de passe ne correspondent pas."
        elif len(nouveau) < 10:
            erreur = "Le mot de passe doit contenir au moins 10 caractères."
        else:
            request.user.set_password(nouveau)
            request.user.doit_changer_mot_de_passe = False
            request.user.date_dernier_changement_mdp = timezone.now()
            request.user.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)  # évite une déconnexion immédiate
            return redirect('dashboard:index')

    return render(request, "authentication/changer_mot_de_passe.html", {"erreur": erreur})
# ----- Fin securite

##@login_required
def utilisateur_dashboard(request):
    resultat = lister_utilisateurs(page=1, page_size=10)
    contexte = {
        "roles_utilisateur": User.UserRole.choices,
        "specialites_disponibles": Specialite.objects.all().order_by("libelle"),
        "resultats_initiaux": resultat["resultats"],
        "pagination_initiale": resultat["pagination"],
    }
    #print("Le contxte --> ",contexte)
    print("Le resultat --> ",resultat)

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
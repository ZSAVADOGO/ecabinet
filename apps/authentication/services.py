# authentication/services.py
"""
Couche service pour le module Utilisateur.
Toute la logique métier (recherche, pagination, validation, CRUD) est isolée
ici pour rester indépendante des vues (contrôleurs) et testable unitairement.

Miroir de client/services.py, adapté au modèle User (AbstractUser) :
- "nom" / "prenom" sont des @property qui proxient last_name / first_name.
  Ce ne sont PAS des colonnes SQL : toute recherche/tri doit passer par les
  vrais champs (last_name, first_name), jamais par nom__icontains.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, Value, CharField
from django.db.models.functions import Coalesce, Lower, Concat
from django.db.models.deletion import ProtectedError, RestrictedError

from apps.authentication.models import User, Specialite

#--- Securite
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.utils import timezone
from .models import User, JournalConnexion
#--- Fin securite


# Champs réels sur lesquels porte la recherche libre (nom/prenom = propriétés,
# on cible donc last_name/first_name directement).
CHAMPS_RECHERCHE = ["last_name", "first_name", "email", "telephone_direct", "username"]

CHAMPS_TRI_MAPPING = {
    "role": "role",
    "nom": "nom_tri",                      # champ calculé (last_name + first_name)
    "email": "email",
    "departement": "departement",
    "telephone_direct": "telephone_direct",
    "date_prestation_serment": "date_prestation_serment",
    "created_at": "created_at",
}



def obtenir_profil_utilisateur(user) -> dict:
    return {
        "id": str(user.id),
        "nom": user.last_name,
        "prenom": user.first_name,
        "nom_complet": f"{user.first_name} {user.last_name}".strip() or user.username,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "role_libelle": user.get_role_display(),
        "departement": user.departement,
        "telephone_direct": user.telephone_direct,
        "telephone2": user.telephone2,
        "date_prestation_serment": user.date_prestation_serment.strftime("%d/%m/%Y") if user.date_prestation_serment else None,
        "annees_experience": user.annees_experience,
        "taux_horaire_defaut": str(user.taux_horaire_defaut) if user.taux_horaire_defaut is not None else None,
        "specialites": [s.libelle for s in user.specialites.all()],
        "derniere_connexion_ip": user.derniere_connexion_ip,
        "date_dernier_changement_mdp": user.date_dernier_changement_mdp.strftime("%d/%m/%Y à %H:%M") if user.date_dernier_changement_mdp else "Jamais modifié",
    }


def modifier_coordonnees_profil(user, payload: dict) -> dict:
    """
    Seules les coordonnées de contact direct sont modifiables par l'utilisateur
    lui-même. Nom, rôle, département, date de prestation de serment restent
    gérés par l'associé (données d'identité judiciaire/hiérarchique du cabinet) —
    évite qu'un collaborateur modifie son propre rôle ou son ancienneté officielle.
    """
    user.telephone_direct = (payload.get("telephone_direct") or "").strip() or None
    user.telephone2 = (payload.get("telephone2") or "").strip() or None
    user.save(update_fields=["telephone_direct", "telephone2"])
    return obtenir_profil_utilisateur(user)


def changer_mot_de_passe_utilisateur(user, ancien_mot_de_passe: str, nouveau_mot_de_passe: str, confirmation: str):
    if not user.check_password(ancien_mot_de_passe):
        raise ValidationError("Le mot de passe actuel est incorrect.")
    if nouveau_mot_de_passe != confirmation:
        raise ValidationError("Les deux mots de passe ne correspondent pas.")
    if ancien_mot_de_passe == nouveau_mot_de_passe:
        raise ValidationError("Le nouveau mot de passe doit être différent de l'ancien.")

    try:
        validate_password(nouveau_mot_de_passe, user=user)
    except DjangoValidationError as exc:
        raise ValidationError(" ".join(exc.messages))

    user.set_password(nouveau_mot_de_passe)
    user.doit_changer_mot_de_passe = False
    user.date_dernier_changement_mdp = timezone.now()
    user.save(update_fields=["password", "doit_changer_mot_de_passe", "date_dernier_changement_mdp"])
    return user

def se_connecter(request, email: str, mot_de_passe: str) -> tuple[bool, str]:
    """
    Retourne (succes: bool, message: str). Ne révèle jamais si c'est l'email
    ou le mot de passe qui est incorrect (mitige l'énumération de comptes).
    """
    print("reception des donnees --> ",request, email, mot_de_passe)

    ip = request.META.get('REMOTE_ADDR', '')
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
    print("Le ip = ",ip," le user_agent = ",user_agent)
    try:
        candidat = User.objects.get(email__iexact=email)
        if candidat.est_verrouille():
            _journaliser(email, ip, user_agent, succes=False)
            return False, "Compte temporairement verrouillé suite à plusieurs échecs. Réessayez dans 15 minutes."
    except User.DoesNotExist:
        pass  # on continue quand même vers authenticate() pour un temps de réponse uniforme

    utilisateur = authenticate(request, username=email, password=mot_de_passe)
    print("tentative de connxeion --> ",utilisateur )
    if utilisateur is None:
        _journaliser(email, ip, user_agent, succes=False)
        return False, "Email ou mot de passe incorrect."

    if not utilisateur.is_active:
        _journaliser(email, ip, user_agent, succes=False)
        return False, "Ce compte a été désactivé. Contactez l'administrateur du cabinet."

    django_login(request, utilisateur)
    _journaliser(email, ip, user_agent, succes=True, utilisateur=utilisateur)
    print("Fonction Journaliser --> ", _journaliser)
    return True, "Connexion réussie."


def se_deconnecter(request):
    print("fonction sedeconnecter / request --> ",request)
    django_logout(request)


def _journaliser(email, ip, user_agent, succes, utilisateur=None):
    JournalConnexion.objects.create(
        utilisateur=utilisateur,
        email_saisi=email,
        adresse_ip=ip,
        user_agent=user_agent,
        succes=succes,
    )

def nom_affichage(utilisateur: User) -> str:
    """Nom complet d'affichage, cohérent avec __str__ du modèle."""
    nom_complet = f"{utilisateur.nom or ''} {utilisateur.prenom or ''}".strip()
    return nom_complet or utilisateur.username


def utilisateur_vers_dict(utilisateur: User) -> dict:
    return {
        "id": str(utilisateur.id),
        "username": utilisateur.username,
        "nom": utilisateur.nom,
        "prenom": utilisateur.prenom,
        "nom_affichage": nom_affichage(utilisateur),
        "email": utilisateur.email,
        "role": utilisateur.role,
        "role_libelle": utilisateur.get_role_display(),
        "departement": utilisateur.departement,
        "telephone_direct": utilisateur.telephone_direct,
        #"numero_toque": utilisateur.numero_toque,
        #"case_barreau": utilisateur.case_barreau,
        "taux_horaire_defaut": float(utilisateur.taux_horaire_defaut) if utilisateur.taux_horaire_defaut is not None else None,
        "date_prestation_serment": utilisateur.date_prestation_serment.strftime("%Y-%m-%d") if utilisateur.date_prestation_serment else None,
        "annees_experience": utilisateur.annees_experience,
        "is_active": utilisateur.is_active,
        "notes": utilisateur.notes,
        "specialites": [
            {"id": str(s.id), "libelle": s.libelle} for s in utilisateur.specialites.all()
        ],
        "specialites_ids": [str(s.id) for s in utilisateur.specialites.all()],
        "created_at": utilisateur.created_at.strftime("%d/%m/%Y %H:%M") if utilisateur.created_at else None,
    }


def lister_utilisateurs(
    recherche: str = "",
    role: str = "",
    date_debut: str = "",
    date_fin: str = "",
    page: int = 1,
    page_size: int = 10,
    tri: str = "-created_at",
):
    """
    Retourne un dict prêt à être sérialisé en JSON pour le tableau du dashboard :
    - recherche libre sur last_name / first_name / email / telephone_direct / username
    - filtre optionnel par rôle
    - filtre optionnel par plage de dates de création (date_debut / date_fin, format YYYY-MM-DD)
    - pagination (page, page_size)
    """
    base_qs = User.objects.all()

    if recherche:
        q_recherche = Q()
        for champ in CHAMPS_RECHERCHE:
            q_recherche |= Q(**{f"{champ}__icontains": recherche})
        base_qs = base_qs.filter(q_recherche)

    if role:
        base_qs = base_qs.filter(role=role)
    if date_debut:
        base_qs = base_qs.filter(created_at__date__gte=_parse_date(date_debut))
    if date_fin:
        base_qs = base_qs.filter(created_at__date__lte=_parse_date(date_fin))

    total = base_qs.count()  # COUNT(*) simple, toujours sans annotation

    # Traduction du champ demandé par le frontend vers le vrai champ SQL à trier
    champ_demande = tri.lstrip('-')
    prefixe = '-' if tri.startswith('-') else ''
    champ_reel = CHAMPS_TRI_MAPPING.get(champ_demande, 'created_at')
    tri_final = f"{prefixe}{champ_reel}"

    page = max(page, 1)
    offset = (page - 1) * page_size
    resultats_page = list(
        base_qs.prefetch_related("specialites").annotate(
            nom_tri=Coalesce(
                Lower(Concat(Coalesce('last_name', Value('')), Value(' '), Coalesce('first_name', Value('')))),
                Value(''),
                output_field=CharField(),
            )
        ).order_by(tri_final)[offset:offset + page_size]
        
    )

    nb_pages = max((total + page_size - 1) // page_size, 1)

    return {
        "resultats": [utilisateur_vers_dict(u) for u in resultats_page],
        "pagination": {
            "page_courante": page,
            "nb_pages": nb_pages,
            "nb_resultats": total,
            "page_size": page_size,
            "a_precedent": page > 1,
            "a_suivant": page < nb_pages,
        },
    }


def obtenir_utilisateur(utilisateur_id) -> User:
    return User.objects.prefetch_related("specialites").get(pk=utilisateur_id)


def creer_utilisateur(payload: dict, utilisateur_courant) -> User:
    _valider_payload(payload, creation=True)

    utilisateur = User(
        username=payload.get("username"),
        email=payload.get("email"),
        role=payload.get("role", User.UserRole.COLLABORATEUR),
        departement=payload.get("departement") or None,
        telephone_direct=payload.get("telephone_direct") or None,
        #numero_toque=payload.get("numero_toque") or None,
        #case_barreau=payload.get("case_barreau") or None,
        taux_horaire_defaut=payload.get("taux_horaire_defaut") or None,
        date_prestation_serment=payload.get("date_prestation_serment") or None,
        notes=payload.get("notes") or None,
        is_active=payload.get("is_active", True),
    )
    utilisateur.nom = payload.get("nom") or ""
    utilisateur.prenom = payload.get("prenom") or ""
    utilisateur.set_password(payload.get("password"))

    utilisateur.full_clean(exclude=["password"])
    try:
        utilisateur.save()
    except IntegrityError:
        raise ValidationError("Cet identifiant ou cet email est déjà utilisé par un autre utilisateur.")

    _assigner_specialites(utilisateur, payload.get("specialites_ids", []))
    return utilisateur


def modifier_utilisateur(utilisateur_id, payload: dict, utilisateur_courant) -> User:
    _valider_payload(payload, creation=False)
    utilisateur = obtenir_utilisateur(utilisateur_id)

    utilisateur.nom = payload.get("nom") or utilisateur.nom
    utilisateur.prenom = payload.get("prenom") or utilisateur.prenom
    utilisateur.email = payload.get("email") or utilisateur.email
    utilisateur.role = payload.get("role", utilisateur.role)
    utilisateur.departement = payload.get("departement") or None
    utilisateur.telephone_direct = payload.get("telephone_direct") or None
    #utilisateur.numero_toque = payload.get("numero_toque") or None
    #utilisateur.case_barreau = payload.get("case_barreau") or None
    utilisateur.taux_horaire_defaut = payload.get("taux_horaire_defaut") or None
    utilisateur.date_prestation_serment = payload.get("date_prestation_serment") or None
    utilisateur.notes = payload.get("notes") or None
    utilisateur.is_active = payload.get("is_active", utilisateur.is_active)

    # Mot de passe : optionnel en modification, on ne touche à rien si vide.
    nouveau_mdp = payload.get("password")
    if nouveau_mdp:
        utilisateur.set_password(nouveau_mdp)

    utilisateur.full_clean(exclude=["password"])
    try:
        utilisateur.save()
    except IntegrityError:
        raise ValidationError("Cet identifiant ou cet email est déjà utilisé par un autre utilisateur.")

    if "specialites_ids" in payload:
        _assigner_specialites(utilisateur, payload.get("specialites_ids", []))

    return utilisateur


def supprimer_utilisateur(utilisateur_id):
    """
    Supprime un utilisateur. Si des objets liés (dossiers gérés, événements créés,
    etc.) sont protégés par on_delete=PROTECT/RESTRICT, Django lève une exception
    qu'on traduit en message métier clair plutôt que de laisser fuiter l'erreur technique.
    """
    utilisateur = obtenir_utilisateur(utilisateur_id)
    try:
        utilisateur.delete()
    except (RestrictedError, ProtectedError):
        raise ValidationError(
            "Impossible de supprimer cet utilisateur : il est rattaché à des dossiers, "
            "événements ou factures existants. Désactivez son compte plutôt que de le supprimer."
        )


def _assigner_specialites(utilisateur: User, specialite_ids):
    if not specialite_ids:
        utilisateur.specialites.clear()
        return
    specialites = Specialite.objects.filter(id__in=specialite_ids)
    utilisateur.specialites.set(specialites)


def _valider_payload(payload: dict, creation: bool):
    if not payload.get("nom"):
        raise ValidationError("Le nom est obligatoire.")
    if not payload.get("prenom"):
        raise ValidationError("Le prénom est obligatoire.")
    if not payload.get("email"):
        raise ValidationError("L'email est obligatoire.")
    if not payload.get("role"):
        raise ValidationError("Le rôle est obligatoire.")

    if creation:
        if not payload.get("username"):
            raise ValidationError("L'identifiant (username) est obligatoire.")
        if not payload.get("password"):
            raise ValidationError("Le mot de passe est obligatoire à la création.")


def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()
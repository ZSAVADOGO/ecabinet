# apps/core/permissions.py — à ajouter à la suite de CAPACITES déjà défini
from apps.authentication.models import User
from apps.core.models import PermissionRole



roles = User.UserRole.choices  # [('associe', 'Associé'), ('avocat', 'Avocat'), ...]

# CODE EN DUrE 

CAPACITES = {
    # Navigation générale
    "voir_dashboard":        {"associe", "avocat", "collaborateur", "secretariat", "stagiaire", "comptable"},
    "voir_clients":          {"associe", "avocat", "collaborateur", "secretariat"},
    "voir_dossiers":         {"associe", "avocat", "collaborateur", "stagiaire"},
    "voir_agenda":           {"associe", "avocat", "collaborateur", "secretariat", "stagiaire"},
    "voir_facturation":      {"associe", "avocat", "comptable"},
    "voir_notifications_sms":{"associe", "avocat", "collaborateur", "secretariat"},
    #"voir_statistiques":     {"associe", "avocat", "comptable"},
    #"voir_statistiques":     {"associe"},
    

    # Actions sensibles (création/modification/suppression)
    "creer_client":          {"associe", "avocat", "collaborateur", "secretariat"},
    "creer_dossier":         {"associe", "avocat", "collaborateur"},
    "modifier_dossier":      {"associe", "avocat", "collaborateur"},
    "supprimer_dossier":     {"associe", "avocat"},
    "creer_agenda":          {"associe", "avocat", "collaborateur", "secretariat"},
    "creer_facture":         {"associe", "comptable"},
    "envoyer_sms":           {"associe", "avocat", "collaborateur", "secretariat"},

    "voir_agenda_dossier":   {"associe", "avocat", "collaborateur", "secretariat"},

    # Administration du cabinet
    "gerer_utilisateurs":    {"associe"},
    "gerer_parametrage":     {"associe"},
    "gerer_fournisseurs_sms":{"associe"},
}
# Fin codé en dure

LIBELLES_CAPACITES = {
    "voir_dashboard":         "Accéder au tableau de bord",
    "voir_clients":           "Consulter le module Clients",
    "voir_dossiers":          "Consulter le module Dossiers",
    "voir_agenda":            "Consulter l'Agenda",
    "voir_facturation":       "Consulter la Facturation",
    "voir_notifications_sms": "Consulter les Notifications SMS",
    "voir_statistiques":      "Consulter les statistiques du cabinet",

    "creer_client":           "Créer un client",
    "creer_dossier":          "Créer un dossier",
    "modifier_dossier":       "Modifier un dossier",
    "supprimer_dossier":      "Supprimer un dossier",
    "creer_agenda":           "Créer un événement d'agenda",
    "creer_facture":          "Créer une facture",
    "envoyer_sms":            "Envoyer une notification SMS",

    "gerer_utilisateurs":     "Gérer les utilisateurs / collaborateurs",
    "gerer_parametrage":      "Accéder au Paramétrage général",
    "gerer_fournisseurs_sms": "Gérer les fournisseurs SMS",
}

CATEGORIES_CAPACITES = {
    "Navigation":         ["voir_dashboard", "voir_clients", "voir_dossiers", "voir_agenda", "voir_facturation", "voir_notifications_sms", "voir_statistiques"],
    "Actions sensibles":  ["creer_client", "creer_dossier", "modifier_dossier", "supprimer_dossier", "creer_agenda", "creer_facture", "envoyer_sms"],
    "Administration":     ["gerer_utilisateurs", "gerer_parametrage", "gerer_fournisseurs_sms"],
}

CAPACITES_VERROUILLEES_POUR_ASSOCIE = {"gerer_utilisateurs", "gerer_parametrage", "gerer_fournisseurs_sms"}


CAPACITES.update({
    "voir_statistiques_juridiques":   {"associe", "avocat", "collaborateur"},
    "voir_statistiques_secretariat":  {"associe", "secretariat"},
    "voir_statistiques_comptable":    {"associe", "comptable"},
})

LIBELLES_CAPACITES.update({
    "voir_statistiques_juridiques":  "Consulter les statistiques juridiques",
    "voir_statistiques_secretariat": "Consulter les statistiques secrétariat",
    "voir_statistiques_comptable":   "Consulter les statistiques comptables",
})

CATEGORIES_CAPACITES["Navigation"] += [
    "voir_statistiques_juridiques", "voir_statistiques_secretariat", "voir_statistiques_comptable"
]


def obtenir_permissions_effectives(user) -> dict:
    """
    Calcule, en une seule passe, la permission effective pour TOUTES les capacités
    d'un coup — à utiliser une fois par requête (context processor), plutôt que
    d'appeler peut() capacité par capacité (ce qui multiplierait les requêtes SQL).
    """
    if not user or not user.is_authenticated:
        return {cle: False for cle in CAPACITES}

    # 1. Valeurs par défaut, codées en dur (le filet de sécurité)
    resultat = {cle: user.role in roles for cle, roles in CAPACITES.items()}

    # 2. Surcharges de rôle stockées en base : UNE requête, tout le rôle d'un coup
    for surcharge in PermissionRole.objects.filter(role=user.role):
        if surcharge.capacite in resultat:  # ignore une capacité qui aurait été supprimée du code
            resultat[surcharge.capacite] = surcharge.autorise

    return resultat


def peut(user, capacite: str) -> bool:
    """Vérification ponctuelle (ex: dans @capacite_requise, appelée une fois par vue)."""
    if capacite not in CAPACITES:
        raise ValueError(f"Capacité inconnue : '{capacite}'.")
    return obtenir_permissions_effectives(user).get(capacite, False)

# OLD
""" def peut(user, capacite: str) -> bool:
   
    if capacite not in CAPACITES:
        raise ValueError(f"Capacité inconnue : '{capacite}'. Vérifiez l'orthographe dans CAPACITES.")
    if not user or not user.is_authenticated:
        return False
    return user.role in CAPACITES[capacite] """

""" def matrice_permissions():
    sections = []
    for categorie, cles in CATEGORIES_CAPACITES.items():
        lignes = []
        for cle in cles:
            lignes.append({
                "cle": cle,
                "libelle": LIBELLES_CAPACITES.get(cle, cle),
                "autorise_par_role": {code: (code in CAPACITES[cle]) for code, _ in roles},
            })
        sections.append({"categorie": categorie, "lignes": lignes})

    return {"roles": roles, "sections": sections} """

def matrice_permissions():
    """
    Construit la matrice rôle × capacité en tenant compte des surcharges
    enregistrées en base (PermissionRole), pas seulement des valeurs par
    défaut codées dans CAPACITES.
    """

    roles = User.UserRole.choices

    # Une seule requête pour TOUTES les surcharges existantes, peu importe le rôle/la capacité
    surcharges = {
        (s.role, s.capacite): s.autorise
        for s in PermissionRole.objects.all()
    }

    sections = []
    for categorie, cles in CATEGORIES_CAPACITES.items():
        lignes = []
        for cle in cles:
            valeurs_par_role = {}
            for code, _ in roles:
                if (code, cle) in surcharges:
                    valeurs_par_role[code] = surcharges[(code, cle)]   # la vraie valeur enregistrée en base
                else:
                    valeurs_par_role[code] = code in CAPACITES[cle]     # valeur par défaut du code, si jamais surchargée
            lignes.append({
                "cle": cle,
                "libelle": LIBELLES_CAPACITES.get(cle, cle),
                "autorise_par_role": valeurs_par_role,
            })
        sections.append({"categorie": categorie, "lignes": lignes})

    return {"roles": roles, "sections": sections}
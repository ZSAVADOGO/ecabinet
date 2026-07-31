# apps/core/permissions.py
"""
Source UNIQUE de vérité pour "qui peut faire quoi" dans eCabinet.
Toute nouvelle fonctionnalité protégée par rôle doit passer par cette table —
jamais de liste de rôles écrite en dur ailleurs (ni dans un template, ni dans une vue).
"""

CAPACITES = {
    # Navigation générale
    "voir_dashboard":        {"associe", "avocat", "collaborateur", "secretariat", "stagiaire", "comptable"},
    "voir_clients":          {"associe", "avocat", "collaborateur", "secretariat"},
    "voir_dossiers":         {"associe", "avocat", "collaborateur", "stagiaire"},
    "voir_agenda":           {"associe", "avocat", "collaborateur", "secretariat", "stagiaire"},
    "voir_facturation":      {"associe", "avocat", "comptable"},
    "voir_notifications_sms":{"associe", "avocat", "collaborateur", "secretariat"},
    #"voir_statistiques":     {"associe", "avocat", "comptable"},
    "voir_statistiques":     {"associe"},

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


def peut(user, capacite: str) -> bool:
    """
    Point d'entrée unique. Lève une erreur explicite si la capacité n'existe pas
    (plutôt qu'un `False` silencieux qui masquerait une faute de frappe).
    """
    if capacite not in CAPACITES:
        raise ValueError(f"Capacité inconnue : '{capacite}'. Vérifiez l'orthographe dans CAPACITES.")
    if not user or not user.is_authenticated:
        return False
    return user.role in CAPACITES[capacite]
# apps/core/context_processors.py
from apps.core.permissions import CAPACITES, peut
from apps.core.permissions import obtenir_permissions_effectives

def permissions_utilisateur(request):
    """
    Calcule une seule fois par requête l'ensemble des permissions de l'utilisateur
    connecté, et les rend disponibles dans TOUS les templates via `permissions.xxx`
    — sans avoir à les recalculer ni les repasser dans le contexte de chaque vue.
    """
    #return {"permissions": {cle: peut(request.user, cle) for cle in CAPACITES}}
    #— mise à jour : un seul appel, pas une boucle
    return {"permissions": obtenir_permissions_effectives(request.user)}
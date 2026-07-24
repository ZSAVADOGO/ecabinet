from django.http import JsonResponse
from django.db.models.deletion import ProtectedError
from django.utils.text import capfirst

# Dictionnaire de traduction UI des modèles pour le cabinet
# Ajoutez ici vos modèles au fur et à mesure pour une traduction propre à l'écran
DICTIONNAIRE_MODELES_UI = {
    'evenementagenda': 'événement(s) d\'agenda',
    'facture': 'facture(s)',
    'partieprenante': 'partie(s) prenante(s)',
    'document': 'document(s) joint(s)',
    'honoraire': 'note(s) d\'honoraires',
}

def gerer_erreur_suppression_protegee(exception_error, nom_entite_a_supprimer="cet élément"):
    """
    Intercepte de façon universelle le blocage de suppression d'une table liée
    et retourne un dictionnaire JSON exploitable en JavaScript.
    """
    if not isinstance(exception_error, ProtectedError):
        return JsonResponse({"success": False, "error": "Une erreur de base de données est survenue."}, status=500)

    # Récupération automatique et unique des noms des tables bloquantes
    tables_liees = set()
    for obj in exception_error.protected_objects:
        # Récupère le nom lisible du modèle Django lié (ex: "événement d'agenda", "facture")
        nom_modele = obj._meta.verbose_name
        tables_liees.add(nom_modele.lower())

    # Construction d'une phrase explicite pour l'avocat
    liste_tables = ", ".join([f"« {t} »" for t in tables_liees])
    
    message_final = (
        f"Impossible de supprimer {nom_entite_a_supprimer}.\n\n"
        f"Cete donnée est actuellement liée ou référencée dans d'autres sections du logiciel : {liste_tables}.\n\n"
        f"Pour des raisons de sécurité juridique et éviter toute perte de données, "
        f"veuillez d'abord retirer cet élément de ces sections avant de pouvoir le supprimer."
    )

    return JsonResponse({
        "success": False,
        "error": message_final
    }, status=400)
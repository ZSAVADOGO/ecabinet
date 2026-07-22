"""
Commande de gestion Django : seed_tribunaux
============================================

Emplacement à respecter :
    <une_app>/management/commands/seed_tribunaux.py

Usage :
    python manage.py seed_tribunaux
    python manage.py seed_tribunaux --flush
"""

import uuid
from django.core.management.base import BaseCommand
from django.db import transaction

# Remplacez "dossier.models" ou "referentiel.models" par le nom exact de votre app
try:
    from authentication.models import Tribunal, TypeTribunal
except ImportError:
    try:
        from authentication.models import Tribunal, TypeTribunal
    except ImportError:
        # Fallback au cas où le modèle s'appelle Juridiction / TypeJuridiction
        from authentication.models import Juridiction as Tribunal, TypeJuridiction as TypeTribunal


# ---------------------------------------------------------------------------
# Données des Types de Tribunaux / Juridictions du Burkina Faso
# ---------------------------------------------------------------------------
TYPES_TRIBUNAUX_DATA = [
    {
        "code": "TGI",
        "libelle": "Tribunal de Grande Instance",
        "description": "Juridiction de droit commun de premier degré statuant en matière civile, commerciale et pénale.",
    },
    {
        "code": "TID",
        "libelle": "Tribunal d'Instance",
        "description": "Juridiction de proximité statuant sur les litiges civils de faible montant et petites infractions.",
    },
    {
        "code": "TC",
        "libelle": "Tribunal de Commerce",
        "description": "Juridiction spécialisée pour les litiges entre commerçants et sociétés commerciales.",
    },
    {
        "code": "TT",
        "libelle": "Tribunal du Travail",
        "description": "Juridiction spécialisée dans les conflits individuels entre employeurs et salariés.",
    },
    {
        "code": "TA",
        "libelle": "Tribunal Administratif",
        "description": "Juridiction saisie des litiges oppposant les citoyens ou entreprises à l'Administration publique.",
    },
    {
        "code": "CA",
        "libelle": "Cour d'Appel",
        "description": "Juridiction du second degré réexaminant les affaires jugées en première instance.",
    },
    {
        "code": "CS",
        "libelle": "Cour Suprême / Conseil d'État",
        "description": "Hautes juridictions de cassation et de contrôle de la légalité.",
    },
    {
        "code": "TCE",
        "libelle": "Tribunal Pour Enfants",
        "description": "Juridiction spécialisée traitant de la délinquance juvénile et de la protection de l'enfance.",
    },
]

# ---------------------------------------------------------------------------
# Carte des Tribunaux par Ville et Type (Burkina Faso)
# ---------------------------------------------------------------------------
TRIBUNAUX_DATA = [
    # --- TGI ---
    {"nom": "Tribunal de Grande Instance de Ouagadougou (Ouaga I)", "type_code": "TGI", "ville": "Ouagadougou", "ressort": "Kadiogo"},
    {"nom": "Tribunal de Grande Instance de Ouaga II", "type_code": "TGI", "ville": "Ouagadougou", "ressort": "Kadiogo"},
    {"nom": "Tribunal de Grande Instance de Bobo-Dioulasso", "type_code": "TGI", "ville": "Bobo-Dioulasso", "ressort": "Houet"},
    {"nom": "Tribunal de Grande Instance de Koudougou", "type_code": "TGI", "ville": "Koudougou", "ressort": "Boulkiemdé"},
    {"nom": "Tribunal de Grande Instance de Banfora", "type_code": "TGI", "ville": "Banfora", "ressort": "Comoé"},
    {"nom": "Tribunal de Grande Instance de Ouahigouya", "type_code": "TGI", "ville": "Ouahigouya", "ressort": "Yatenga"},
    {"nom": "Tribunal de Grande Instance de Fada N'Gourma", "type_code": "TGI", "ville": "Fada N'Gourma", "ressort": "Gourma"},
    {"nom": "Tribunal de Grande Instance de Kaya", "type_code": "TGI", "ville": "Kaya", "ressort": "Sanmatenga"},
    {"nom": "Tribunal de Grande Instance de Tenkodogo", "type_code": "TGI", "ville": "Tenkodogo", "ressort": "Boulgou"},
    {"nom": "Tribunal de Grande Instance de Dédougou", "type_code": "TGI", "ville": "Dédougou", "ressort": "Mouhoun"},
    {"nom": "Tribunal de Grande Instance de Gaoua", "type_code": "TGI", "ville": "Gaoua", "ressort": "Poni"},
    {"nom": "Tribunal de Grande Instance de Dori", "type_code": "TGI", "ville": "Dori", "ressort": "Séno"},
    {"nom": "Tribunal de Grande Instance de Ziniaré", "type_code": "TGI", "ville": "Ziniaré", "ressort": "Oubritenga"},
    {"nom": "Tribunal de Grande Instance de Manga", "type_code": "TGI", "ville": "Manga", "ressort": "Zoundwéogo"},
    {"nom": "Tribunal de Grande Instance de Boromo", "type_code": "TGI", "ville": "Boromo", "ressort": "Balé"},
    {"nom": "Tribunal de Grande Instance de Tougan", "type_code": "TGI", "ville": "Tougan", "ressort": "Sourou"},
    {"nom": "Tribunal de Grande Instance de Yako", "type_code": "TGI", "ville": "Yako", "ressort": "Passoré"},
    {"nom": "Tribunal de Grande Instance de Koupéla", "type_code": "TGI", "ville": "Koupéla", "ressort": "Kouritenga"},
    {"nom": "Tribunal de Grande Instance de Bogandé", "type_code": "TGI", "ville": "Bogandé", "ressort": "Gnagna"},

    # --- Tribunaux Spécialisés ---
    {"nom": "Tribunal de Commerce de Ouagadougou", "type_code": "TC", "ville": "Ouagadougou", "ressort": "Région du Centre"},
    {"nom": "Tribunal de Commerce de Bobo-Dioulasso", "type_code": "TC", "ville": "Bobo-Dioulasso", "ressort": "Région des Hauts-Bassins"},
    {"nom": "Tribunal du Travail de Ouagadougou", "type_code": "TT", "ville": "Ouagadougou", "ressort": "Kadiogo"},
    {"nom": "Tribunal du Travail de Bobo-Dioulasso", "type_code": "TT", "ville": "Bobo-Dioulasso", "ressort": "Houet"},
    {"nom": "Tribunal Administratif de Ouagadougou", "type_code": "TA", "ville": "Ouagadougou", "ressort": "Région du Centre"},
    {"nom": "Tribunal Administratif de Bobo-Dioulasso", "type_code": "TA", "ville": "Bobo-Dioulasso", "ressort": "Région des Hauts-Bassins"},

    # --- Cours d'Appel ---
    {"nom": "Cour d'Appel de Ouagadougou", "type_code": "CA", "ville": "Ouagadougou", "ressort": "Centre, Plateau-Central, Centre-Sud, etc."},
    {"nom": "Cour d'Appel de Bobo-Dioulasso", "type_code": "CA", "ville": "Bobo-Dioulasso", "ressort": "Hauts-Bassins, Cascades, Boucle du Mouhoun, Sud-Ouest"},
    {"nom": "Cour d'Appel de Fada N'Gourma", "type_code": "CA", "ville": "Fada N'Gourma", "ressort": "Est, Centre-Est"},

    # --- Juridictions Supérieures ---
    {"nom": "Conseil d'État du Burkina Faso", "type_code": "CS", "ville": "Ouagadougou", "ressort": "National"},
    {"nom": "Cour de Cassation du Burkina Faso", "type_code": "CS", "ville": "Ouagadougou", "ressort": "National"},
]


class Command(BaseCommand):
    help = "Insère le référentiel complet des types de tribunaux et tribunaux du Burkina Faso."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Purge les tables des tribunaux et types de tribunaux avant insertion.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write(self.style.WARNING("Purge des tribunaux et types existants..."))
            Tribunal.objects.all().delete()
            TypeTribunal.objects.all().delete()

        with transaction.atomic():
            types_dict = self._creer_types_tribunaux()
            tribunaux = self._creer_tribunaux(types_dict)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Insertion terminée avec succès !\n"
            f"   - Types de tribunaux créés : {len(types_dict)}\n"
            f"   - Tribunaux créés          : {len(tribunaux)}"
        ))

    def _creer_types_tribunaux(self):
        """Crée ou récupère les types de tribunaux."""
        types_dict = {}
        type_objs = []

        # Récupérer les champs du modèle TypeTribunal pour construire dynamiquement les arguments
        fields = [f.name for f in TypeTribunal._meta.get_fields()]

        for item in TYPES_TRIBUNAUX_DATA:
            kwargs = {}
            if "id" in fields:
                kwargs["id"] = uuid.uuid4()

            # Mapper les champs selon votre modèle (nom ou libelle)
            if "libelle" in fields:
                kwargs["libelle"] = item["libelle"]
            elif "nom" in fields:
                kwargs["nom"] = item["libelle"]

            if "code" in fields:
                kwargs["code"] = item["code"]

            if "description" in fields:
                kwargs["description"] = item["description"]

            obj = TypeTribunal(**kwargs)
            type_objs.append(obj)
            types_dict[item["code"]] = obj

        TypeTribunal.objects.bulk_create(type_objs, ignore_conflicts=True)

        # Si ignore_conflicts est utilisé ou si les UUIDs posent souci, réassocier depuis la BDD
        types_db = TypeTribunal.objects.all()
        for t in types_db:
            code = getattr(t, "code", None)
            if code:
                types_dict[code] = t

        return types_dict

    def _creer_tribunaux(self, types_dict):
        """Crée les instances de tribunaux associées à leur type."""
        tribunal_objs = []
        fields = [f.name for f in Tribunal._meta.get_fields()]

        for item in TRIBUNAUX_DATA:
            type_obj = types_dict.get(item["type_code"])
            
            kwargs = {}
            if "id" in fields:
                kwargs["id"] = uuid.uuid4()

            if "nom" in fields:
                kwargs["nom"] = item["nom"]
            elif "libelle" in fields:
                kwargs["libelle"] = item["nom"]

            if "ville" in fields:
                kwargs["ville"] = item["ville"]

            if "ressort" in fields:
                kwargs["ressort"] = item["ressort"]
            elif "notes" in fields:
                kwargs["notes"] = f"Ressort : {item['ressort']}"

            # Détection du nom du champ ForeignKey vers TypeTribunal
            if "type_tribunal" in fields:
                kwargs["type_tribunal"] = type_obj
            elif "type" in fields:
                kwargs["type"] = type_obj
            elif "type_juridiction" in fields:
                kwargs["type_juridiction"] = type_obj

            tribunal_objs.append(Tribunal(**kwargs))

        Tribunal.objects.bulk_create(tribunal_objs, ignore_conflicts=True)
        return tribunal_objs
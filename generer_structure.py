import os

STRUCTURE = {
    "authentication": {
        "models.py": (
            "import uuid\n"
            "from django.contrib.auth.models import AbstractUser\n"
            "from django.db import models\n\n"
            "class User(AbstractUser):\n"
            "    class UserRole(models.TextChoices):\n"
            "        ASSOCIE = 'associe', 'Associé'\n"
            "        AVOCAT = 'avocat', 'Avocat'\n"
            "        COLLABORATEUR = 'collaborateur', 'Collaborateur'\n"
            "        SECRETARIAT = 'secretariat', 'Secrétariat'\n"
            "        STAGIAIRE = 'stagiaire', 'Stagiaire'\n\n"
            "    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
            "    email = models.EmailField(unique=True)\n"
            "    role = models.CharField(\n"
            "        max_length=20,\n"
            "        choices=UserRole.choices,\n"
            "        default=UserRole.COLLABORATEUR,\n"
            "        db_index=True\n"
            "    )\n"
            "    created_at = models.DateTimeField(auto_now_add=True)\n"
            "    updated_at = models.DateTimeField(auto_now=True)\n\n"
            "    # Django utilise l'email pour l'authentification si souhaité, sinon username par défaut\n"
            "    REQUIRED_FIELDS = ['email', 'nom', 'prenom']\n\n"
            "    class Meta:\n"
            "        db_table = 'users'\n"
        ),
        "services.py": "# Authentification & Droits d'accès\n",
        "controllers.py": "from django.shortcuts import render\n",
        "urls.py": "from django.urls import path\napp_name = 'authentication'\nurlpatterns = []\n"
    },
    "dashboard": {
        "models.py": "# Modèles pour l'application dashboard\nfrom django.db import models\n",
        "services.py": (
            "# Logique métier et agrégats pour le tableau de bord\n"
            "from django.db.models import Count, Sum\n"
            "from dossier.models import Dossier\n"
            "from facturation.models import Facture\n\n"
            "class DashboardMetricsService:\n"
            "    @staticmethod\n"
            "    def obtenir_donnees_graphiques():\n"
            "        stats_dossiers = Dossier.objects.values('statut').annotate(total=Count('id'))\n"
            "        stats_ca = Facture.objects.filter(statut='payee').values('dossier__type_affaire').annotate(total_ca=Sum('montant_ht'))\n"
            "        return {'graphique_statuts': list(stats_dossiers), 'graphique_ca': list(stats_ca)}\n"
        ),
        "controllers.py": (
            "from django.shortcuts import render\n"
            "from rest_framework.decorators import api_view\n"
            "from rest_framework.response import Response\n"
            "from dashboard.services import DashboardMetricsService\n\n"
            "def page_accueil(request):\n"
            "    return render(request, 'dashboard/index.html')\n\n"
            "@api_view(['GET'])\n"
            "def api_metrics_graphiques(request):\n"
            "    return Response(DashboardMetricsService.obtenir_donnees_graphiques())\n"
        ),
        "urls.py": (
            "from django.urls import path\n"
            "from dashboard import controllers\n\n"
            "app_name = 'dashboard'\n\n"
            "urlpatterns = [\n"
            "    path('', controllers.page_accueil, name='index'),\n"
            "    path('api/metrics/', controllers.api_metrics_graphiques, name='api_metrics'),\n"
            "]\n"
        ),
        "template_file": "index.html",
        "html_content": (
            "{% extends 'base.html' %}\n{% block content %}\n"
            "<h1>Tableau de bord de présentation</h1>\n"
            "<div style='display: flex; gap: 20px;'>\n"
            "    <div style='width: 400px;'><canvas id='pieDossiers'></canvas></div>\n"
            "    <div style='width: 400px;'><canvas id='pieFinance'></canvas></div>\n"
            "</div>\n"
            "<script>\n"
            "    fetch('{% url \"dashboard:api_metrics\" %}')\n"
            "        .then(res => res.json())\n"
            "        .then(data => { /* Code Chart.js */ });\n"
            "</script>\n{% endblock %}\n"
        )
    },
    "client": {
        "models.py": (
            "import uuid\n"
            "from django.db import models\n"
            "from django.conf import settings\n\n"
            "# Classe mère de traçabilité globale\n"
            "class AuditableModel(models.Model):\n"
            "    created_at = models.DateTimeField(auto_now_add=True, db_index=True)\n"
            "    updated_at = models.DateTimeField(auto_now=True)\n"
            "    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_creations')\n"
            "    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_modifications')\n\n"
            "    class Meta:\n"
            "        abstract = True\n\n"
            "class Client(AuditableModel):\n"
            "    class ClientType(models.TextChoices):\n"
            "        PERSONNE_PHYSIQUE = 'personne_physique', 'Personne Physique'\n"
            "        PERSONNE_MORALE = 'personne_morale', 'Personne Morale'\n\n"
            "    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
            "    type = models.CharField(max_length=20, choices=ClientType.choices, default=ClientType.PERSONNE_PHYSIQUE, db_index=True)\n"
            "    nom_complet = models.CharField(max_length=255, db_index=True)\n"
            "    email = models.EmailField(null=True, blank=True)\n"
            "    telephone = models.CharField(max_length=30, null=True, blank=True)\n"
            "    adresse = models.TextField(null=True, blank=True)\n"
            "    siret = models.CharField(max_length=20, null=True, blank=True)  # Spécifique personnes morales\n"
            "    notes = models.TextField(null=True, blank=True)\n\n"
            "    class Meta:\n"
            "        db_table = 'clients'\n"
        ),
        "services.py": "class ClientService:\n    pass\n",
        "controllers.py": "from django.shortcuts import render\n",
        "serializers.py": "from rest_framework import serializers\n",
        "urls.py": (
            "from django.urls import path\n"
            "from django.http import HttpResponse\n\n"
            "app_name = 'client'\n\n"
            "urlpatterns = [\n"
            "    path('', lambda request: HttpResponse('Page Liste des Clients...'), name='liste'),\n"
            "]\n"
        ),
        "template_file": "client_dashboard.html",
        "html_content": "{% extends 'base.html' %}\n{% block content %}\n<h1>CRM Clients</h1>\n{% endblock %}\n"
    },
    "dossier": {
        "models.py": (
            "import uuid\n"
            "from django.db import models\n"
            "from django.conf import settings\n"
            "from client.models import Client, AuditableModel\n\n"
            "class Dossier(AuditableModel):\n"
            "    class StatutDossier(models.TextChoices):\n"
            "        OUVERT = 'ouvert', 'Ouvert'\n"
            "        EN_COURS = 'en_cours', 'En cours'\n"
            "        PLAIDE = 'plaide', 'Plaidé'\n"
            "        CLOS = 'clos', 'Clos'\n"
            "        ARCHIVE = 'archive', 'Archivé'\n\n"
            "    class TypeAffaire(models.TextChoices):\n"
            "        CIVIL = 'civil', 'Civil'\n"
            "        PENAL = 'penal', 'Pénal'\n"
            "        COMMERCIAL = 'commercial', 'Commercial'\n"
            "        SOCIAL = 'social', 'Social'\n"
            "        FAMILLE = 'famille', 'Famille'\n"
            "        ADMINISTRATIF = 'administratif', 'Administratif'\n"
            "        AUTRE = 'autre', 'Autre'\n\n"
            "    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
            "    reference = models.CharField(max_length=50, unique=True, db_index=True)  # ex: DOS-2026-0001\n"
            "    intitule = models.CharField(max_length=255)\n"
            "    type_affaire = models.CharField(max_length=20, choices=TypeAffaire.choices, default=TypeAffaire.AUTRE, db_index=True)\n"
            "    statut = models.CharField(max_length=20, choices=StatutDossier.choices, default=StatutDossier.OUVERT, db_index=True)\n\n"
            "    # Jointure avec Client (onDelete: 'RESTRICT')\n"
            "    client = models.ForeignKey(Client, on_delete=models.RESTRICT, related_name='dossiers')\n\n"
            "    # Jointure avec l'Avocat Référent (User)\n"
            "    avocat_referent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_referes')\n\n"
            "    juridiction = models.CharField(max_length=255, null=True, blank=True)\n"
            "    date_ouverture = models.DateField(null=True, blank=True)\n"
            "    date_prochaine_echeance = models.DateField(null=True, blank=True, db_index=True)  # Délai de procédure critique\n"
            "    description = models.TextField(null=True, blank=True)\n\n"
            "    class Meta:\n"
            "        db_table = 'dossiers'\n"
        ),
        "services.py": "# Logique métier Dossier\n",
        "controllers.py": "from django.shortcuts import render\n",
        "serializers.py": "from rest_framework import serializers\n",
        "urls.py": (
            "from django.urls import path\n"
            "from django.http import HttpResponse\n\n"
            "app_name = 'dossier'\n\n"
            "urlpatterns = [\n"
            "    path('', lambda request: HttpResponse('Page Liste des Dossiers...'), name='liste'),\n"
            "]\n"
        ),
        "template_file": "dossiers_dashboard.html",
        "html_content": "{% extends 'base.html' %}\n{% block content %}\n<h1>Gestion des Dossiers</h1>\n{% endblock %}\n"
    },
    "documents": {
        "models.py": (
            "import uuid\n"
            "from django.db import models\n"
            "from client.models import AuditableModel\n"
            "from dossier.models import Dossier\n\n"
            "class DocumentEntity(AuditableModel):\n"
            "    class TypeDocument(models.TextChoices):\n"
            "        CONTRAT = 'contrat', 'Contrat'\n"
            "        CONCLUSION = 'conclusion', 'Conclusion'\n"
            "        JUGEMENT = 'jugement', 'Jugement'\n"
            "        PIECE_ADVERSE = 'piece_adverse', 'Pièce Adverse'\n"
            "        COURRIER = 'courrier', 'Courrier'\n"
            "        AUTRE = 'autre', 'Autre'\n\n"
            "    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
            "    nom = models.CharField(max_length=255)\n"
            "    type = models.CharField(max_length=20, choices=TypeDocument.choices, default=TypeDocument.AUTRE, db_index=True)\n"
            "    chemin_stockage = models.CharField(max_length=500)  # Lien vers stockage (S3 ou local)\n"
            "    version = models.IntegerField(default=1)\n\n"
            "    # Jointure avec Dossier (onDelete: CASCADE)\n"
            "    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='documents')\n\n"
            "    class Meta:\n"
            "        db_table = 'documents'\n"
        ),
        "services.py": "# GED\n",
        "controllers.py": "from django.shortcuts import render\n",
        "urls.py": "from django.urls import path\napp_name = 'documents'\nurlpatterns = []\n",
        "template_file": "ged_dashboard.html",
        "html_content": "{% extends 'base.html' %}\n{% block content %}\nGED\n{% endblock %}\n"
    },
    "agenda": {
        "models.py": (
            "import uuid\n"
            "from django.db import models\n"
            "from client.models import AuditableModel\n"
            "from dossier.models import Dossier\n\n"
            "class EvenementAgenda(AuditableModel):\n"
            "    class TypeEvenement(models.TextChoices):\n"
            "        AUDIENCE = 'audience', 'Audience'\n"
            "        RDV_CLIENT = 'rdv_client', 'Rendez-vous Client'\n"
            "        DELAI_PROCEDURE = 'delai_procedure', 'Délai Procédure'\n"
            "        AUTRE = 'autre', 'Autre'\n\n"
            "    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
            "    titre = models.CharField(max_length=255)\n"
            "    type = models.CharField(max_length=20, choices=TypeEvenement.choices, default=TypeEvenement.AUTRE, db_index=True)\n"
            "    date_heure = models.DateTimeField(db_index=True)\n"
            "    critique = models.BooleanField(default=False)  # Forclusion -> Alerte renforcée\n\n"
            "    # Jointure avec Dossier (onDelete: CASCADE, nullable: true)\n"
            "    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, null=True, blank=True, related_name='evenements')\n\n"
            "    class Meta:\n"
            "        db_table = 'evenements_agenda'\n"
        ),
        "services.py": "# Calcul délais\n",
        "controllers.py": "from django.shortcuts import render\n",
        "urls.py": (
            "from django.urls import path\n\n"
            "app_name = 'agenda'\n\n"
            "urlpatterns = []\n"
        ),
        "template_file": "calendar.html",
        "html_content": "{% extends 'base.html' %}\n{% block content %}\nAgenda\n{% endblock %}\n"
    },
    "facturation": {
        "models.py": (
            "import uuid\n"
            "from django.db import models\n"
            "from client.models import Client, AuditableModel\n"
            "from dossier.models import Dossier\n\n"
            "class Facture(AuditableModel):\n"
            "    class StatutFacture(models.TextChoices):\n"
            "        BROUILLON = 'brouillon', 'Brouillon'\n"
            "        ENVOYEE = 'envoyee', 'Envoyée'\n"
            "        PAYEE = 'payee', 'Payée'\n"
            "        EN_RETARD = 'en_retard', 'En retard'\n\n"
            "    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)\n"
            "    numero = models.CharField(max_length=50, unique=True, db_index=True)\n"
            "    client = models.ForeignKey(Client, on_delete=models.RESTRICT, related_name='factures')\n"
            "    dossier = models.ForeignKey(Dossier, on_delete=models.SET_NULL, null=True, blank=True, related_name='factures')\n"
            "    montant_ht = models.DecimalField(max_digits=10, decimal_places=2)\n"
            "    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)\n"
            "    statut = models.CharField(max_length=20, choices=StatutFacture.choices, default=StatutFacture.BROUILLON, db_index=True)\n"
            "    date_emission = models.DateField()\n"
            "    date_echeance = models.DateField(null=True, blank=True)\n\n"
            "    class Meta:\n"
            "        db_table = 'factures'\n"
        ),
        "services.py": "# Saisie des temps, compta CARPA\n",
        "controllers.py": "from django.shortcuts import render\n",
        "urls.py": "from django.urls import path\napp_name = 'facturation'\nurlpatterns = []\n",
        "template_file": "billing_dashboard.html",
        "html_content": "{% extends 'base.html' %}\n{% block content %}\nFacturation\n{% endblock %}\n"
    },
    "portal": {
        "models.py": "from django.db import models\nfrom client.models import AuditableModel\n",
        "services.py": "# Espace client\n",
        "controllers.py": "from django.shortcuts import render\n",
        "urls.py": "from django.urls import path\napp_name = 'portal'\nurlpatterns = []\n",
        "template_file": "client_home.html",
        "html_content": "{% extends 'base.html' %}\n{% block content %}\nExtranet\n{% endblock %}\n"
    }
}


def generer_architecture():
    base_apps_dir = os.path.join(os.getcwd(), "apps")
    os.makedirs(base_apps_dir, exist_ok=True)

    for app_name, fichiers in STRUCTURE.items():
        app_dir = os.path.join(base_apps_dir, app_name)
        template_dir = os.path.join(app_dir, "templates", app_name)
        os.makedirs(template_dir, exist_ok=True)

        # Création du fichier d'initialisation obligatoire pour Django (__init__.py)
        with open(os.path.join(app_dir, "__init__.py"), "w") as f:
            f.write("")

        # Création de apps.py
        with open(os.path.join(app_dir, "apps.py"), "w") as f:
            f.write(
                f"from django.apps import AppConfig\n\n"
                f"class {app_name.capitalize()}Config(AppConfig):\n"
                f"    default_auto_field = 'django.db.models.BigAutoField'\n"
                f"    name = '{app_name}'\n"
            )

        # Génération des fichiers Python internes (.py)
        for file_name, content in fichiers.items():
            if file_name.endswith(".py"):
                with open(os.path.join(app_dir, file_name), "w", encoding="utf-8") as f:
                    f.write(content)

        # Génération du fichier HTML si présent
        if "template_file" in fichiers:
            html_file = fichiers["template_file"]
            html_content = fichiers["html_content"]
            with open(os.path.join(template_dir, html_file), "w", encoding="utf-8") as f:
                f.write(html_content)

    print("✅ Base de données mise à jour et harmonisée. Les modèles TypeORM sont traduits pour l'ORM Django.")


if __name__ == "__main__":
    generer_architecture()
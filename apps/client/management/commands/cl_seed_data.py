"""
Commande de gestion Django : seed_data
=======================================

Emplacement à respecter (Django n'auto-découvre les commandes qu'à cet endroit
précis, dans une app INSTALLED_APPS) :

    <une_app>/management/commands/seed_data.py

Par exemple dans l'app `client` :

    client/
        management/
            __init__.py                <- fichier vide
            commands/
                __init__.py            <- fichier vide
                seed_data.py           <- ce fichier

`management/` et `management/commands/` doivent chacun contenir un
`__init__.py` (même vide) pour être reconnus comme packages Python.

Usage :
    python manage.py seed_data                # insère les données
    python manage.py seed_data --flush        # vide les tables concernées puis réinsère
"""

import random
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from client.models import Client
from dossier.models import Dossier
from agenda.models import EvenementAgenda
from facturation.models import Facture

from apps.authentication.models import User

#User = get_user_model()

random.seed(42)

# ---------------------------------------------------------------------------
# Référentiels "contexte Burkina Faso"
# ---------------------------------------------------------------------------

PRENOMS_HOMMES = [
    "Boureima", "Issouf", "Salif", "Adama", "Moussa", "Ousmane", "Idrissa",
    "Yacouba", "Abdoulaye", "Seydou", "Rasmané", "Ibrahim", "Souleymane",
    "Hamidou", "Karim", "Wendinmi", "Wendkuni", "Zakaria", "Lassané",
    "Sibiri", "Boubacar", "Amadou", "Drissa", "Paulin", "Emmanuel",
]
PRENOMS_FEMMES = [
    "Aminata", "Fatimata", "Awa", "Mariam", "Rasmata", "Bintou", "Salamata",
    "Assita", "Kadidia", "Rokia", "Habibou", "Alimata", "Djénéba",
    "Wendlassida", "Rachelle", "Clarisse", "Elisabeth", "Sandrine",
    "Adjara", "Korotoumou", "Ramata", "Pauline", "Sévérine", "Nathalie",
]
NOMS_FAMILLE = [
    "Ouédraogo", "Kaboré", "Sawadogo", "Compaoré", "Zongo", "Traoré",
    "Ilboudo", "Nikiéma", "Kologo", "Bassolé", "Kafando", "Kagambèga",
    "Tapsoba", "Sanou", "Kambou", "Coulibaly", "Konaté", "Somé",
    "Yaméogo", "Bado", "Ouali", "Dabiré", "Ganamé", "Kiéma", "Nabaloum",
    "Bicaba", "Zerbo", "Diallo", "Barry", "Sanogo", "Guigma", "Ouoba",
]
VILLES = [
    "Ouagadougou", "Bobo-Dioulasso", "Koudougou", "Banfora", "Ouahigouya",
    "Kaya", "Tenkodogo", "Fada N'Gourma", "Dédougou", "Gaoua", "Dori",
    "Ziniaré", "Réo", "Manga",
]
SECTEURS_QUARTIERS = [
    "Secteur 15", "Secteur 30", "Zone du Bois", "Ouaga 2000", "Gounghin",
    "Dassasgho", "Tampouy", "Pissy", "Zogona", "Cissin", "Karpala",
    "Patte d'Oie", "Kilwin", "Somgandé",
]
VOIES = [
    "Avenue Kwamé N'Krumah", "Avenue de la Nation", "Avenue Bassawarga",
    "Avenue Charles de Gaulle", "Boulevard Circulaire", "Rue de la Palmeraie",
    "Avenue de l'Indépendance", "Rue 15.35",
]
PREFIXES_MOBILES = ["70", "71", "72", "74", "75", "76", "77", "78"]
JURIDICTIONS = [
    "Tribunal de Grande Instance de Ouagadougou",
    "Tribunal de Grande Instance de Bobo-Dioulasso",
    "Cour d'Appel de Ouagadougou",
    "Cour d'Appel de Bobo-Dioulasso",
    "Tribunal du Travail de Ouagadougou",
    "Tribunal de Commerce de Ouagadougou",
    "Tribunal Administratif de Ouagadougou",
    "Conseil d'État du Burkina Faso",
]
FORMES_ENTREPRISE = ["SARL", "SA", "Ets", "SUARL", "Groupe"]
MOTS_ENTREPRISE = [
    "Faso", "Wend-Panga", "Sahel", "Cauris", "Nazemsé", "Yiriba",
    "Bâtir", "Import-Export", "Commerce Général", "Négoce", "Services",
    "BTP", "Transit", "Distribution",
]
DOMAINES_PERSO = ["gmail.com", "yahoo.fr", "outlook.com"]

TYPES_AFFAIRE = ["civil", "penal", "commercial", "social", "famille", "administratif", "autre"]
STATUTS_DOSSIER = ["ouvert", "en_cours", "plaide", "clos", "archive"]
TYPES_EVENEMENT = ["audience", "rdv_client", "delai_procedure", "autre"]
STATUTS_FACTURE = ["brouillon", "envoyee", "payee", "en_retard"]
ROLES = ["associe", "avocat", "collaborateur", "secretariat", "stagiaire"]

TITRES_PAR_TYPE = {
    "audience": ["Audience de plaidoirie", "Audience de mise en état", "Audience de référé", "Audience correctionnelle"],
    "rdv_client": ["RDV client - point d'étape", "RDV client - signature", "RDV client - premier entretien"],
    "delai_procedure": ["Délai de conclusions", "Délai d'appel", "Forclusion - dépôt de pièces", "Délai de prescription"],
    "autre": ["Réunion interne", "Formation", "Rédaction de conclusions", "Relecture contrat"],
}

TAUX_TVA_BF = 18.00
TODAY = date.today()
SIX_YEARS_AGO = TODAY - timedelta(days=365 * 6)


# ---------------------------------------------------------------------------
# Générateurs "faker maison" contexte Burkina Faso
# ---------------------------------------------------------------------------

def prenom_nom(genre=None):
    genre = genre or random.choice(["H", "F"])
    prenom = random.choice(PRENOMS_HOMMES if genre == "H" else PRENOMS_FEMMES)
    nom = random.choice(NOMS_FAMILLE)
    return prenom, nom


def telephone_bf():
    prefixe = random.choice(PREFIXES_MOBILES)
    reste = f"{random.randint(0, 99):02d} {random.randint(0, 99):02d} {random.randint(0, 99):02d}"
    return f"+226 {prefixe} {reste}"


def adresse_bf():
    ville = random.choice(VILLES)
    quartier = random.choice(SECTEURS_QUARTIERS)
    if random.random() < 0.5:
        voie = random.choice(VOIES)
        return f"{voie}, {quartier}, {ville}"
    return f"{quartier}, {ville}"


def ifu_bf():
    return f"{random.randint(10_000_000, 99_999_999)}{random.choice('ABCDEFGHJ')}"


def nom_entreprise():
    forme = random.choice(FORMES_ENTREPRISE)
    mots = random.sample(MOTS_ENTREPRISE, k=2)
    return f"{forme} {mots[0]} {mots[1]}"


def email_perso(prenom, nom):
    domaine = random.choice(DOMAINES_PERSO)
    base = f"{prenom}.{nom}".lower().replace(" ", "").replace("'", "")
    return f"{base}{random.randint(1, 99)}@{domaine}"


def email_entreprise(nom_ent):
    slug = "".join(c for c in nom_ent.lower() if c.isalnum())
    return f"contact@{slug}.bf"


def phrase_intitule():
    themes = [
        "Litige commercial fournisseur", "Contentieux de succession",
        "Rupture abusive de contrat de travail", "Recouvrement de créance",
        "Contentieux foncier", "Divorce et garde d'enfants",
        "Constitution de société", "Contentieux administratif - permis",
        "Bail commercial - expulsion", "Accident de la circulation",
        "Vol et recel", "Litige de voisinage", "Créance impayée - fournisseur BTP",
        "Contrat de distribution", "Diffamation",
    ]
    return random.choice(themes)


def note_client():
    notes = [
        "Client fidèle depuis plusieurs années.", "Recommandé par un confrère.",
        "Dossier suivi en urgence.", "Client basé hors de Ouagadougou.",
        "Préfère être contacté par téléphone.", None, None,
    ]
    return random.choice(notes)


def description_dossier():
    return (
        "Dossier ouvert pour le compte du client concernant un litige de type "
        f"{random.choice(TYPES_AFFAIRE)}. Suivi assuré par le cabinet, "
        "pièces en cours de constitution."
    )


def date_entre(debut: date, fin: date) -> date:
    if fin <= debut:
        return debut
    delta = (fin - debut).days
    return debut + timedelta(days=random.randint(0, delta))


def datetime_entre(debut: date, fin: date) -> datetime:
    d = date_entre(debut, fin)
    naive = datetime.combine(d, datetime.min.time()) + timedelta(
        hours=random.randint(7, 18), minutes=random.choice([0, 15, 30, 45])
    )
    return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


class Command(BaseCommand):
    help = (
        "Génère un jeu de données de test (contexte Burkina Faso) et l'insère "
        "directement dans la base configurée dans settings.py via l'ORM Django."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Supprime les données existantes de ces tables avant de réinsérer.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Suppression des données existantes...")
            Facture.objects.all().delete()
            EvenementAgenda.objects.all().delete()
            Dossier.objects.all().delete()
            Client.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        with transaction.atomic():
            users = self._creer_users(n=8)
            clients = self._creer_clients(users)
            dossiers = self._creer_dossiers(clients, users)
            evenements = self._creer_evenements(dossiers, users, n=50)
            factures = self._creer_factures(clients, dossiers, users, n=60)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Seed terminé : {len(users)} utilisateurs, {len(clients)} clients, "
            f"{len(dossiers)} dossiers, {len(evenements)} événements, "
            f"{len(factures)} factures."
        ))
        annees = sorted({f.date_emission.year for f in factures})
        self.stdout.write(f"Années couvertes par les factures : {annees}")

    # -----------------------------------------------------------------
    # 1. Utilisateurs
    # -----------------------------------------------------------------
    def _creer_users(self, n=8):
        objs = []
        for i in range(n):
            genre = random.choice(["H", "F"])
            prenom, nom = prenom_nom(genre)
            role = random.choice(["associe", "avocat"]) if i < 5 else ROLES[i % len(ROLES)]
            date_joined = datetime_entre(SIX_YEARS_AGO, TODAY - timedelta(days=180))
            objs.append(User(
                username=f"{prenom.lower()}.{nom.lower()}{i}",
                prenom=prenom,
                nom=nom,
                email=f"{prenom.lower()}.{nom.lower()}{i}@cabinet-avocats.bf",
                password=make_password("123456"),  # mot de passe par défaut pour le seed
                is_staff=role in ("associe", "avocat"),
                is_active=True,
                date_joined=date_joined,
                role=role,
            ))
        User.objects.bulk_create(objs)
        # created_at (auto_now_add) est forcé à "now" par bulk_create -> on le backdate
        for obj in objs:
            obj.created_at = obj.date_joined
        User.objects.bulk_update(objs, ["created_at"])
        return objs

    # -----------------------------------------------------------------
    # 2. Clients
    # -----------------------------------------------------------------
    """ def _creer_clients(self, users, n=20):
        objs = []
        created_ats = []
        for _ in range(n):
            ctype = random.choice(["personne_physique", "personne_morale"])
            created_at = datetime_entre(SIX_YEARS_AGO, TODAY - timedelta(days=30))
            if ctype == "personne_physique":
                genre = random.choice(["H", "F"])
                prenom, nom = prenom_nom(genre)
                nom_complet = f"{prenom} {nom}"
                email = email_perso(prenom, nom)
                siret = None
            else:
                nom_complet = nom_entreprise()
                email = email_entreprise(nom_complet)
                siret = ifu_bf()

            obj = Client(
                type=ctype,
                nom_complet=nom_complet,
                email=email,
                telephone=telephone_bf(),
                adresse=adresse_bf(),
                siret=siret,
                notes=note_client(),
                created_by=random.choice(users),
                edited_by=random.choice(users) if random.random() < 0.6 else None,
            )
            objs.append(obj)
            created_ats.append(created_at)

        Client.objects.bulk_create(objs)
        for obj, created_at in zip(objs, created_ats):
            obj.created_at = created_at
        Client.objects.bulk_update(objs, ["created_at"])
        return objs """
    
    def _creer_clients(self, users):
        objs = []
        created_ats = []
        
        # Configuration stricte demandée : (type, quantité)
        configuration_clients = [
            (Client.ClientType.PERSONNE_MORALE, 20),
            (Client.ClientType.PERSONNE_PHYSIQUE, 10)
        ]
        
        for ctype, quantite in configuration_clients:
            for _ in range(quantite):
                created_at = datetime_entre(SIX_YEARS_AGO, TODAY - timedelta(days=30))
                
                # Initialisation par défaut des champs du modèle
                nom = ""
                prenom = ""
                raison_sociale = ""
                ifu_rccm = None
                
                if ctype == Client.ClientType.PERSONNE_PHYSIQUE:
                    genre = random.choice(["H", "F"])
                    prenom, nom = prenom_nom(genre)
                    email = email_perso(prenom, nom)
                else:
                    # Personne morale
                    raison_sociale = nom_entreprise()
                    email = email_entreprise(raison_sociale)
                    ifu_rccm = ifu_bf()
                
                # Sélection des utilisateurs pour l'auditabilité
                user_createur = random.choice(users)
                user_editeur = random.choice(users) if random.random() < 0.6 else None

                obj = Client(
                    type=ctype,
                    nom=nom,
                    prenom=prenom,
                    raison_sociale=raison_sociale,
                    ifu_rccm=ifu_rccm,
                    email=email,
                    telephone1=telephone_bf(),
                    telephone2=None, # Laissé vide par défaut
                    adresse=adresse_bf(),
                    notes=note_client(),
                    created_by=user_createur,
                    edited_by=user_editeur,
                )
                objs.append(obj)
                created_ats.append(created_at)

        # Insertion de masse optimisée (Remplit les UUID automatiques)
        Client.objects.bulk_create(objs)
        
        # Rétrogradage des dates de création (Fix auto_now_add de l'AuditableModel)
        for obj, created_at in zip(objs, created_ats):
            obj.created_at = created_at
        Client.objects.bulk_update(objs, ["created_at"])
        
        return objs

    # -----------------------------------------------------------------
    # 3. Dossiers (3 ou 4 par client)
    # -----------------------------------------------------------------
    def _creer_dossiers(self, clients, users):
        avocats = [u for u in users if u.role in ("associe", "avocat")]
        objs = []
        created_ats = []
        ref_counter = 1
        for client in clients:
            nb_dossiers = random.choice([3, 4])
            for _ in range(nb_dossiers):
                statut = random.choice(STATUTS_DOSSIER)
                date_ouverture = date_entre(client.created_at.date(), TODAY)
                annee = date_ouverture.year
                date_prochaine_echeance = None
                if statut in ("ouvert", "en_cours"):
                    date_prochaine_echeance = min(
                        date_ouverture + timedelta(days=random.randint(15, 240)),
                        TODAY + timedelta(days=180),
                    )
                obj = Dossier(
                    reference=f"DOS-{annee}-{ref_counter:04d}",
                    intitule=phrase_intitule(),
                    type_affaire=random.choice(TYPES_AFFAIRE),
                    statut=statut,
                    client=client,
                    avocat_referent=random.choice(avocats),
                    juridiction=random.choice(JURIDICTIONS),
                    date_ouverture=date_ouverture,
                    date_prochaine_echeance=date_prochaine_echeance,
                    description=description_dossier(),
                    created_by=random.choice(users),
                    edited_by=random.choice(users) if random.random() < 0.5 else None,
                )
                objs.append(obj)
                created_ats.append(datetime.combine(date_ouverture, datetime.min.time()))
                ref_counter += 1

        Dossier.objects.bulk_create(objs)
        for obj, created_at in zip(objs, created_ats):
            obj.created_at = timezone.make_aware(created_at) if timezone.is_naive(created_at) else created_at
        Dossier.objects.bulk_update(objs, ["created_at"])
        return objs

    # -----------------------------------------------------------------
    # 4. Événements d'agenda (50)
    # -----------------------------------------------------------------
    def _creer_evenements(self, dossiers, users, n=50):
        objs = []
        for i in range(n):
            type_evt = TYPES_EVENEMENT[i % len(TYPES_EVENEMENT)]
            dossier = random.choice(dossiers) if random.random() < 0.85 else None
            borne_min = dossier.date_ouverture if dossier else SIX_YEARS_AGO
            date_heure = datetime_entre(borne_min, TODAY + timedelta(days=180))
            critique = type_evt == "delai_procedure" and random.random() < 0.6
            objs.append(EvenementAgenda(
                titre=random.choice(TITRES_PAR_TYPE[type_evt]),
                type=type_evt,
                date_heure=date_heure,
                critique=critique,
                dossier=dossier,
                created_by=random.choice(users),
            ))
        EvenementAgenda.objects.bulk_create(objs)
        return objs

    # -----------------------------------------------------------------
    # 5. Factures (60, réparties sur 6 ans)
    # -----------------------------------------------------------------
    def _creer_factures(self, clients, dossiers, users, n=60):
        objs = []
        created_ats = []
        for i in range(n):
            statut = STATUTS_FACTURE[i % len(STATUTS_FACTURE)]
            client = random.choice(clients)
            dossiers_client = [d for d in dossiers if d.client_id == client.id]
            dossier = random.choice(dossiers_client) if dossiers_client and random.random() < 0.8 else None

            borne_min = max(SIX_YEARS_AGO, dossier.date_ouverture) if dossier else SIX_YEARS_AGO
            date_emission = date_entre(borne_min, TODAY)
            annee = date_emission.year

            date_echeance = None
            if statut != "brouillon":
                date_echeance = date_emission + timedelta(days=30)

            montant_ht = float(random.randint(50, 3000) * 500)  # multiples de 500 FCFA

            objs.append(Facture(
                numero=f"FACT-{annee}-{i + 1:04d}",
                client=client,
                dossier=dossier,
                montant_ht=montant_ht,
                taux_tva=TAUX_TVA_BF,
                statut=statut,
                date_emission=date_emission,
                date_echeance=date_echeance,
                created_by=random.choice(users),
            ))
            created_ats.append(datetime.combine(date_emission, datetime.min.time()))

        Facture.objects.bulk_create(objs)
        for obj, created_at in zip(objs, created_ats):
            obj.created_at = timezone.make_aware(created_at) if timezone.is_naive(created_at) else created_at
        Facture.objects.bulk_update(objs, ["created_at"])
        return objs
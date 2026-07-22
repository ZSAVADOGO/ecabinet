"""
Commande de gestion Django : seed_data
=======================================

Emplacement à respecter :
    <une_app>/management/commands/seed_data.py

Usage :
    python manage.py seed_data
    python manage.py seed_data --flush
"""

import random
import uuid
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

# Import adaptatif pour le modèle Specialite s'il existe
try:
    from client.models import Specialite
except ImportError:
    try:
        from user.models import Specialite
    except ImportError:
        Specialite = None

User = get_user_model()

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

SPECIALITES_DATA = [
    ("Droit des affaires", "Expertise approfondie en droit des sociétés, contrats commerciaux et F&A."),
    ("Droit du travail & social", "Gestion des litiges prud'homaux et rédaction de contrats de travail."),
    ("Droit foncier & immobilier", "Contentieux relatif à la propriété foncière, baux ruraux et commerciaux."),
    ("Droit pénal", "Défense d'urgence, assistance lors de garde à vue et contentieux pénal général."),
    ("Droit de la famille", "Divorce, pensions alimentaires, régimes matrimoniaux et successions."),
    ("Droit commercial", "Recouvrement de créances impayées et contentieux inter-entreprises."),
    ("Droit administratif", "Recours en annulation, marchés publics et contentieux des collectivités."),
]

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
# Fonctions d'assistance
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
    help = "Génère un jeu de données de test calibré pour le cabinet d'avocats."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Supprime les données existantes des tables cibles avant la génération.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Purge des données existantes...")
            Facture.objects.all().delete()
            EvenementAgenda.objects.all().delete()
            Dossier.objects.all().delete()
            Client.objects.all().delete()
            if Specialite and hasattr(Specialite, 'objects'):
                Specialite.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        with transaction.atomic():
            specialites = self._creer_specialites()
            users = self._creer_users(specialites)
            clients = self._creer_clients(users)
            dossiers = self._creer_dossiers(clients, users)
            evenements = self._creer_evenements_dossiers(dossiers, users)
            factures = self._creer_factures(clients, dossiers, users, n=60)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Génération réussie :\n"
            f"   - Utilisateurs : {len(users)} (4 Associés, 2 Avocats, 4 Stagiaires, 1 Secrétaire, 1 Comptable)\n"
            f"   - Clients      : {len(clients)} (20 Morales, 10 Physiques)\n"
            f"   - Dossiers     : {len(dossiers)} (26 clients avec 1 à 3 dossiers, 4 clients sans dossier)\n"
            f"   - Événements   : {len(evenements)} (min. 1 par dossier)\n"
            f"   - Factures     : {len(factures)}"
        ))

    # -----------------------------------------------------------------
    # 0. Spécialités
    # -----------------------------------------------------------------
    def _creer_specialites(self):
        if not Specialite or not hasattr(Specialite, 'objects'):
            return []
        
        objs = []
        for nom, note in SPECIALITES_DATA:
            objs.append(Specialite(
                id=uuid.uuid4(),
                nom=nom,
                note=note
            ))
        Specialite.objects.bulk_create(objs, ignore_conflicts=True)
        return list(Specialite.objects.all())

    # -----------------------------------------------------------------
    # 1. Utilisateurs (Exactement : 4 associés, 2 avocats, 4 stagiaires, 1 secrétaire, 1 comptable = 12 users)
    # -----------------------------------------------------------------
    def _creer_users(self, specialites_disponibles):
        roles_exacts = (
            ["associe"] * 4 +
            ["avocat"] * 2 +
            ["stagiaire"] * 4 +
            ["secretariat"] * 1 +
            ["comptable"] * 1
        )
        
        objs = []
        for i, role in enumerate(roles_exacts):
            genre = random.choice(["H", "F"])
            prenom, nom = prenom_nom(genre)
            date_joined = datetime_entre(SIX_YEARS_AGO, TODAY - timedelta(days=180))
            
            # Gestion de la spécialité selon le modèle configuré
            spec_obj = random.choice(specialites_disponibles) if (role in ("associe", "avocat") and specialites_disponibles) else None
            spec_nom, spec_note = random.choice(SPECIALITES_DATA) if role in ("associe", "avocat") else (None, None)

            user_kwargs = {
                "id": uuid.uuid4(),
                "username": f"{prenom.lower()}.{nom.lower()}{i}",
                "prenom": prenom,
                "nom": nom,
                "email": f"{prenom.lower()}.{nom.lower()}{i}@cabinet-avocats.bf",
                "password": make_password("123456"),
                "is_staff": role in ("associe", "avocat", "comptable"),
                "is_active": True,
                "date_joined": date_joined,
                "role": role,
            }

            # Injecter la spécialité si le champ existe sur le modèle User
            user_fields = [f.name for f in User._meta.get_fields()]
            if "specialite" in user_fields:
                user_kwargs["specialite"] = spec_obj if spec_obj else spec_nom
            if "note" in user_fields and spec_note:
                user_kwargs["note"] = spec_note

            objs.append(User(**user_kwargs))

        User.objects.bulk_create(objs)
        for obj in objs:
            obj.created_at = obj.date_joined
        User.objects.bulk_update(objs, ["created_at"])
        return objs

    # -----------------------------------------------------------------
    # 2. Clients (30 clients : 20 personnes morales, 10 personnes physiques)
    # -----------------------------------------------------------------
    def _creer_clients(self, users):
        objs = []
        created_ats = []
        
        distribution = [
            (Client.ClientType.PERSONNE_MORALE, 20),
            (Client.ClientType.PERSONNE_PHYSIQUE, 10)
        ]
        
        for ctype, quantite in distribution:
            for _ in range(quantite):
                created_at = datetime_entre(SIX_YEARS_AGO, TODAY - timedelta(days=30))
                
                if ctype == Client.ClientType.PERSONNE_PHYSIQUE:
                    genre = random.choice(["H", "F"])
                    prenom, nom = prenom_nom(genre)
                    raison_sociale = ""
                    ifu_rccm = None
                    email = email_perso(prenom, nom)
                else:
                    prenom, nom = "", ""
                    raison_sociale = nom_entreprise()
                    ifu_rccm = ifu_bf()
                    email = email_entreprise(raison_sociale)
                
                obj = Client(
                    id=uuid.uuid4(),
                    type=ctype,
                    nom=nom,
                    prenom=prenom,
                    raison_sociale=raison_sociale,
                    ifu_rccm=ifu_rccm,
                    email=email,
                    telephone1=telephone_bf(),
                    telephone2=None,
                    adresse=adresse_bf(),
                    notes=note_client(),
                    created_by=random.choice(users),
                    edited_by=random.choice(users) if random.random() < 0.4 else None,
                )
                objs.append(obj)
                created_ats.append(created_at)

        Client.objects.bulk_create(objs)
        for obj, created_at in zip(objs, created_ats):
            obj.created_at = created_at
        Client.objects.bulk_update(objs, ["created_at"])
        
        return objs

    # -----------------------------------------------------------------
    # 3. Dossiers (26 clients avec 1 à 3 dossiers, 4 clients avec 0 dossier)
    # -----------------------------------------------------------------
    def _creer_dossiers(self, clients, users):
        # Filtrer uniquement les associés et avocats pour être référents
        avocats_referents = [u for u in users if u.role in ("associe", "avocat")]
        
        # Mélanger la liste des clients
        shuffled_clients = list(clients)
        random.shuffle(shuffled_clients)

        # 4 clients désignés sans dossier
        clients_sans_dossier = set(shuffled_clients[:4])
        clients_avec_dossiers = shuffled_clients[4:]

        objs = []
        created_ats = []
        ref_counter = 1

        for client in clients_avec_dossiers:
            # Répartition 1, 2 ou 3 dossiers
            nb_dossiers = random.choice([1, 2, 3])
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
                    id=uuid.uuid4(),
                    reference=f"DOS-{annee}-{ref_counter:04d}",
                    intitule=phrase_intitule(),
                    type_affaire=random.choice(TYPES_AFFAIRE),
                    statut=statut,
                    client=client,
                    avocat_referent=random.choice(avocats_referents),
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
    # 4. Événements d'agenda (Garanti : au moins 1 événement par dossier)
    # -----------------------------------------------------------------
    def _creer_evenements_dossiers(self, dossiers, users):
        objs = []
        for dossier in dossiers:
            # 1 à 3 événements pour chaque dossier afin de respecter le minimum obligatoire
            nb_events = random.randint(1, 3)
            for _ in range(nb_events):
                type_evt = random.choice(TYPES_EVENEMENT)
                date_heure = datetime_entre(dossier.date_ouverture, TODAY + timedelta(days=120))
                critique = (type_evt == "delai_procedure" and random.random() < 0.6)

                objs.append(EvenementAgenda(
                    id=uuid.uuid4(),
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
    # 5. Factures (60 factures réparties sur les clients)
    # -----------------------------------------------------------------
    def _creer_factures(self, clients, dossiers, users, n=60):
        objs = []
        created_ats = []

        # Ne facturer que les personnes ayant au moins un dossier de préférence
        clients_facturables = [c for c in clients if any(d.client_id == c.id for d in dossiers)]
        if not clients_facturables:
            clients_facturables = clients

        for i in range(n):
            statut = STATUTS_FACTURE[i % len(STATUTS_FACTURE)]
            client = random.choice(clients_facturables)
            dossiers_client = [d for d in dossiers if d.client_id == client.id]
            dossier = random.choice(dossiers_client) if dossiers_client else None

            borne_min = max(SIX_YEARS_AGO, dossier.date_ouverture) if dossier else SIX_YEARS_AGO
            date_emission = date_entre(borne_min, TODAY)
            annee = date_emission.year

            date_echeance = None
            if statut != "brouillon":
                date_echeance = date_emission + timedelta(days=30)

            montant_ht = float(random.randint(50, 3000) * 500)
            taux_tva = TAUX_TVA_BF
            montant_ttc = round(montant_ht * (1 + taux_tva / 100.0), 2)

            objs.append(Facture(
                id=uuid.uuid4(),
                numero=f"FACT-{annee}-{i + 1:04d}",
                client=client,
                dossier=dossier,
                montant_ht=montant_ht,
                taux_tva=taux_tva,
                montant_ttc=montant_ttc,
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
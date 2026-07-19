import datetime
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

# Importation de vos modèles Django
from client.models import Client
from dossier.models import Dossier
from agenda.models import EvenementAgenda
from facturation.models import Facture

User = get_user_model()

# --- DONNÉES DE CONTEXTE BURKINABÈ ---
NOMS_PHYSIQUES = [
    "Ouédraogo Aminata", "Sawadogo Issaka", "Traoré Mamadou", "Diallo Boubacar",
    "Barry Fatoumata", "Ilboudo Pascal", "Sorgho Adama", "Zoungrana Windyam",
    "Kaboré Ablassé", "Compaoré Christiane", "Sanou Lassina", "Coulibaly Djénéba",
    "Konaté Ibrahim", "Ki-Zerbo Joseph", "Yameogo Roch", "Tiendrébéogo Pingdwendé",
    "Tall Hama", "Nikiéma Salimata", "Diko Amadou", "Boni Nazaire"
]

ENTREPRISES_BURKINA = [
    ("SOB BRA Burkina", "IFU00012457A"), ("SOCIETE MINIERE DE ESSAKANE", "IFU00054782B"),
    ("TELECEL FASO", "IFU00098521C"), ("SONABHY", "IFU00032145D"),
    ("SONABEL", "IFU00065478E"), ("CORIS BANK INTERNATIONAL", "IFU00011122F"),
    ("CFAO MOTORS BURKINA", "IFU00033344G"), ("ONATEL SA", "IFU00055566H"),
    ("SOCIETE BURKINABE DE FIBRES TEXTILES (SOFITEX)", "IFU00077788I"), ("VIMAS Burkina", "IFU00099900J")
]

VILLES_QUARTIERS = [
    "Ouagadougou (Patte d'Oie)", "Ouagadougou (Daspasogo)", "Bobo-Dioulasso (Sya)",
    "Koudougou (Secteur 3)", "Ouahigouya", "Banfora", "Fada N'Gourma"
]

JURIDICTIONS_BF = [
    "Tribunal de Grande Instance (TGI) Ouaga I",
    "Tribunal de Grande Instance (TGI) Ouaga II",
    "Tribunal de Commerce de Ouagadougou",
    "Cour d'Appel de Ouagadougou",
    "Tribunal de Grande Instance (TGI) de Bobo-Dioulasso",
    "Conseil d'État (Section Contentieux)",
    "Tribunal du Travail de Ouagadougou"
]

class Command(BaseCommand):
    help = "Génère et insère automatiquement un jeu de données de test (Burkina Faso) dans MySQL."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Début du seeding de la base de données..."))

        # 1. Création ou récupération de l'avocat référent
        avocat, created = User.objects.get_or_create(
            username="maitre_ouedraogo",
            defaults={
                "email": "contact@ouedraogo-avocats.bf",
                "prenom": "Maitre",
                "nom": "Ouédraogo",
                "role": "avocat",
                "is_active": True
            }
        )
        if created:
            avocat.set_password("MotDePasseSecurise123!")
            avocat.save()

        # Nettoyage optionnel pour éviter les doublons lors des tests successifs
        Client.objects.all().delete()
        EvenementAgenda.objects.all().delete()
        Facture.objects.all().delete()

        clients_crees = []
        dossiers_crees = []

        # 2. SEEDING DES CLIENTS (20)
        for i in range(20):
            is_physique = i < 12
            if is_physique:
                nom = NOMS_PHYSIQUES[i % len(NOMS_PHYSIQUES)]
                type_c = Client.ClientType.PERSONNE_PHYSIQUE
                siret = None
                email = f"{nom.lower().replace(' ', '.')}@gmail.com"
            else:
                ent, ifu = ENTREPRISES_BURKINA[(i - 12) % len(ENTREPRISES_BURKINA)]
                nom = ent
                type_c = Client.ClientType.PERSONNE_MORALE
                siret = ifu
                email = f"contact@{(nom.lower().split()[0])}.bf"

            tel = f"+226 {random.randint(60, 79)} {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}"
            adresse = f"{random.choice(VILLES_QUARTIERS)}, Burkina Faso"

            client = Client.objects.create(
                type=type_c,
                nom_complet=nom,
                email=email,
                telephone=tel,
                adresse=adresse,
                siret=siret,
                notes="Client importé via script de seed.",
                created_by=avocat
            )
            clients_crees.append(client)

        # 3. SEEDING DES DOSSIERS (3 à 4 par client)
        dossier_compteur = 1
        for client in clients_crees:
            nb_dossiers = random.randint(3, 4)
            for _ in range(nb_dossiers):
                ref = f"DOS-2026-{dossier_compteur:04d}"
                
                if client.type == Client.ClientType.PERSONNE_MORALE:
                    t_affaire = random.choice(['commercial', 'social', 'administratif'])
                    intitule = f"Contentieux d'affaires / {client.nom_complet}"
                else:
                    t_affaire = random.choice(['civil', 'penal', 'famille'])
                    intitule = f"Dossier d'assistance / {client.nom_complet}"

                date_ouv = datetime.date(2026, random.randint(1, 6), random.randint(1, 28))
                date_ech = date_ouv + datetime.timedelta(days=random.randint(30, 180))

                dossier = Dossier.objects.create(
                    reference=ref,
                    intitule=intitule,
                    type_affaire=t_affaire,
                    statut=random.choice(['ouvert', 'en_cours', 'plaide']),
                    client=client,
                    avocat_referent=avocat,
                    juridiction=random.choice(JURIDICTIONS_BF),
                    date_ouverture=date_ouv,
                    date_prochaine_echeance=date_ech,
                    description="Dossier initialisé automatiquement.",
                    created_by=avocat
                )
                dossiers_crees.append(dossier)
                dossier_compteur += 1

        # 4. SEEDING DE L'AGENDA (50 événements)
        types_evenements = ['audience', 'rdv_client', 'delai_procedure', 'autre']
        for i in range(50):
            type_e = random.choice(types_evenements)
            critique = type_e in ['audience', 'delai_procedure'] and random.random() > 0.5
            dt_evt = datetime.datetime(2026, random.randint(7, 12), random.randint(1, 28), random.randint(8, 17), 0)
            
            target_dossier = random.choice(dossiers_crees) if random.random() > 0.2 else None
            
            EvenementAgenda.objects.create(
                titre=f"Événement de suivi N°{i+1}",
                type=type_e,
                date_heure=dt_evt,
                critique=critique,
                dossier=target_dossier,
                created_by=avocat
            )

        # 5. SEEDING DES FINANCES (60 factures)
        statuts_facture = ['brouillon', 'envoyee', 'payee', 'en_retard']
        for i in range(60):
            chosen_dossier = random.choice(dossiers_crees)
            date_em = datetime.date(2026, random.randint(1, 6), random.randint(1, 28))
            
            Facture.objects.create(
                numero=f"FAC-2026-{i+1:04d}",
                client=chosen_dossier.client,
                dossier=chosen_dossier,
                montant_ht=round(random.uniform(250000, 5000000), 2),
                taux_tva=20.00,
                statut=random.choice(statuts_facture),
                date_emission=date_em,
                date_echeance=date_em + datetime.timedelta(days=30),
                created_by=avocat
            )

        self.stdout.write(self.style.SUCCESS("🎉 Base de données MySQL mise à jour avec succès avec le contexte burkinabè !"))
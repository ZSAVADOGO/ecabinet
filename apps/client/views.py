# client/views.py
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db import transaction  # Résout "transaction" is not defined

from django.utils import timezone  # Pour gérer la date d'émission de la facture
import uuid # Pour générer un numéro de facture temporaire unique si besoin

from client.models import Client
from dossier.models import Dossier
from agenda.models import EvenementAgenda
from facturation.models import Facture

# CORRECTION : On importe directement les fonctions autonomes du fichier services
from client.services import obtenir_client, lister_clients, creer_client, modifier_client, supprimer_client, client_vers_dict

from django.contrib.auth import get_user_model # <-- Ajouté pour récupérer le modèle User

User = get_user_model()


def client_creation_wizard(request):
    # Cette vue se contente d'afficher le fichier HTML du formulaire multi-pages
    return render(request, "client/ajout_client.html")

##@login_required 
def client_dashboard(request):
    resultat = lister_clients(page=1, page_size=10)
    contexte = {
        "types_client": Client.ClientType.choices,
        "resultats_initiaux": resultat["resultats"],
        "pagination_initiale": resultat["pagination"],
    }
    return render(request, "client/client_dashboard.html", contexte)


@require_GET
def api_lister_clients(request):
    resultat = lister_clients(
        recherche=request.GET.get("q", "").strip(),
        type_client=request.GET.get("type", ""),
        date_debut=request.GET.get("date_debut", ""),
        date_fin=request.GET.get("date_fin", ""),
        page=int(request.GET.get("page", 1)),
        page_size=int(request.GET.get("page_size", 10)),
        tri=request.GET.get("tri", "-created_at"),   # <- si cette ligne manque, tri n'est JAMAIS transmis
    )
    return JsonResponse(resultat, status=200)


##@login_required
@require_GET
def api_detail_client(request, client_id):
    try:
        client = obtenir_client(client_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Client introuvable."}, status=404)
    return JsonResponse(client_vers_dict(client), status=200)


##@login_required
@require_POST
def api_creer_client(request):
    print("La request reçue --> ", request)
    
    # 🛠️ DÉSACTIVATION DE LA SÉCURITÉ POUR LES TESTS
    user_pour_test = request.user
    if not user_pour_test.is_authenticated:
        user_pour_test = User.objects.first()
        if not user_pour_test:
            user_pour_test = User.objects.create_user(
                username="testuser", 
                email="test@example.com", 
                password="password123"
            )

    try:
        with transaction.atomic():
            data = json.loads(request.body)
            print("La data reçue --> ", data)

            if 'client' not in data:
                return JsonResponse({'erreur': "Le bloc de données 'client' est obligatoire."}, status=400)
            c = data['client']
            # 1. Création du Client
            client = Client.objects.create(
                type=c['type'], nom=c.get('nom'), prenom=c.get('prenom'),
                raison_sociale=c.get('raison_sociale'), ifu_rccm=c.get('ifu_rccm'),
                email=c.get('email'), telephone1=c.get('telephone1'), telephone2=c.get('telephone2'),
                adresse=c.get('adresse'), notes=c.get('notes'),
                created_by=user_pour_test
            )
            dossier, facture, agenda = None, None, None
            # Extraction sécurisée des sous-blocs ou dictionnaires par défaut de simulation
            d = data.get('dossier', {})
            f = data.get('facture', {})
            a = data.get('agenda', {})
            # 2. Création du Dossier
            if 'dossier' in data:
                dossier = Dossier.objects.create(
                    client_id=client.id, 
                    avocat_referent=user_pour_test,
                    intitule=d['intitule'], type_affaire=d['type_affaire'], statut=d['statut'],
                    juridiction=d.get('juridiction'), 
                    date_ouverture=d.get('date_ouverture') or None,
                    date_prochaine_echeance=d.get('date_prochaine_echeance') or None, 
                    description=d.get('description'),
                    created_by=user_pour_test
                )
            # 3. Création des composants dépendants
            if dossier and dossier.id:
                if 'facture' in data:                    
                    # --- DÉBUT DU GÉNÉRATEUR SÉQUENTIEL ---
                    annee_actuelle = timezone.now().strftime("%Y") # Récupère "2026"
                    prefixe = f"FAC-{annee_actuelle}-"
                    # On recherche la dernière facture créée cette année (ex: FAC-2026-0042)
                    derniere_facture = Facture.objects.filter(
                        numero__startswith=prefixe
                    ).order_by('-numero').first()
                    if derniere_facture:
                        # On extrait la partie numérique (les 4 derniers caractères) et on l'incrémente
                        dernier_compteur = int(derniere_facture.numero.split('-')[-1])
                        nouveau_compteur = dernier_compteur + 1
                    else:
                        # C'est la toute première facture de l'année
                        nouveau_compteur = 1
                    # On formate le numéro sur 4 chiffres avec des zéros au début (ex: 0001)
                    numero_sequentiel = f"{prefixe}{nouveau_compteur:04d}"
                    # --- FIN DU GÉNÉRATEUR SÉQUENTIEL ---
                    Facture.objects.create(
                        client_id=client.id,
                        dossier_id=dossier.id, 
                        numero=numero_sequentiel,  # <-- Votre numéro propre : FAC-2026-0001
                        montant_ht=f.get('montant_ht') or 0,
                        montant_ttc=f.get('montant_ttc') or 0, 
                        taux_tva=f.get('taux_tva') or 20.00,
                        statut=f.get('statut', 'brouillon'),
                        date_emission=timezone.now().date(),
                        date_echeance=f.get('date_echeance') or None, 
                        description=f.get('description'),
                        created_by=user_pour_test
                    )
                if 'agenda' in data:
                    EvenementAgenda.objects.create(
                        dossier_id=dossier.id, 
                        titre=a['titre'], 
                        type=a['type'],
                        date_heure=a.get('date_heure') or timezone.now(), 
                        critique=a.get('critique', False),
                        created_by=user_pour_test
                    )
            else:
                if 'facture' in data or 'agenda' in data:
                    raise ValueError("Impossible de configurer une facture ou un agenda sans dossier associé.")
            info_c = client.raison_sociale if client.type == 'personne_morale' else f"{client.nom or ''} {client.prenom or ''}".strip()
            summary = f"<b>👤 Client :</b> {info_c or 'Inconnu'}"
            
            ref_dossier = getattr(dossier, 'reference', None) or dossier.intitule
            
            #summary += f"<b>📂 Dossier :</b> Ref: {str(dossier.id)[:8].upper()} / {dossier.intitule}<br>"


            if dossier or facture or agenda:
                summary += f"<br><b>📂 Dossier :</b> Ref: {ref_dossier} / {dossier.intitule}<br>"
                summary += f"<br><b>💳 Facture :</b> Ref: {facture.numero} / Mnt TTC: {float(facture.montant_ttc):,.0f}".replace(",", " ") + " F CFA"
                summary += f"<br><b>📅 Agenda :</b> {'🚨 ' if agenda.critique else ''}Titre: {agenda.titre} / Date: {agenda.date_heure.strftime('%d/%m/%Y à %H:%M')}"

        return JsonResponse({'message': summary, 'redirect': '/clients/'})

    except KeyError as ke:
        print(f"⚠️ Erreur de champ manquant : {str(ke)}")
        return JsonResponse({'erreur': f"Le paramètre obligatoire suivant est manquant : {str(ke)}"}, status=400)
    except Exception as e:
        print(f"⚠️ Erreur applicative générale : {str(e)}")
        return JsonResponse({'erreur': str(e)}, status=400) 

##@login_required
@require_http_methods(["POST"])
def api_modifier_client(request, client_id):
    try:
        payload = json.loads(request.body)
        client = modifier_client(client_id, payload, request.user)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Client introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"erreur": "Requête invalide (JSON malformé)."}, status=400)

    return JsonResponse(
        {"message": "Client modifié avec succès.", "client": client_vers_dict(client)},
        status=200,
    )


##@login_required
@require_http_methods(["POST"])
def api_supprimer_client(request, client_id):
    try:
        supprimer_client(client_id)
    except ObjectDoesNotExist:
        return JsonResponse({"erreur": "Client introuvable."}, status=404)
    except ValidationError as exc:
        return JsonResponse({"erreur": _message_validation(exc)}, status=400)

    return JsonResponse({"message": "Client supprimé avec succès."}, status=200)

def _filtres_export(request):
    return {
        "recherche": request.GET.get("q", "").strip(),
        "type_client": request.GET.get("type", ""),
        "date_debut": request.GET.get("date_debut", ""),
        "date_fin": request.GET.get("date_fin", ""),
    }


##@login_required
@require_GET
def api_exporter_clients_csv(request):
    contenu = exporter_clients_csv(**_filtres_export(request))
    reponse = HttpResponse(contenu, content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = 'attachment; filename="clients.csv"'
    return reponse


##@login_required
@require_GET
def api_exporter_clients_excel(request):
    classeur = exporter_clients_excel(**_filtres_export(request))
    reponse = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    reponse["Content-Disposition"] = 'attachment; filename="clients.xlsx"'
    classeur.save(reponse)
    return reponse


def _message_validation(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(f"{v[0]}" for v in exc.message_dict.values())
    return " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)

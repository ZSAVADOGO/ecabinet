# agenda/services/agenda_service.py
"""
Couche service du module Agenda.
Modèle de référence : EvenementAgenda (table `evenements_agenda`)
    id, titre, type (audience|rdv_client|delai_procedure|autre), date_heure,
    critique (bool), dossier (FK Dossier, nullable), created_by, edited_by,
    created_at, updated_at.
"""

from datetime import datetime, date, time

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q

from django.http import JsonResponse
from django.shortcuts import get_object_or_404


from django.db import transaction
from agenda.models import EvenementAgenda, PartiePrenante, RolePartiePrenante

from dossier.models import Dossier


ROLES_DICT = dict(RolePartiePrenante.choices)

#CHAMPS_RECHERCHE = ["titre", "dossier__reference", "dossier__intitule"]
CHAMPS_RECHERCHE = [
    "titre",
    "description",
    "dossier__reference",
    "dossier__intitule",
    "responsables__first_name",
    "responsables__last_name",
    "parties_prenantes__nom",
]


def palier_urgence(evt: EvenementAgenda) -> str | None:
    if not evt.critique or not evt.date_heure:
        return None
    jours_restants = (evt.date_heure.date() - date.today()).days
    if jours_restants <= 2:
        return "DERNIER RAPPEL"
    if jours_restants <= 8:
        return "RAPPEL N°2"
    if jours_restants <= 15:
        return "RAPPEL N°1"
    return None


def evenement_vers_dict(evt: EvenementAgenda) -> dict:
    return {
        "id": str(evt.id),
        "titre": evt.titre,
        "type": evt.type,
        "type_libelle": evt.get_type_display(),
        "type_delai": evt.type_delai,
        "type_delai_libelle": evt.get_type_delai_display() if evt.type_delai else None,
        "date_heure": evt.date_heure.isoformat() if evt.date_heure else None,
        "date_echeance_calculee": evt.date_echeance_calculee.isoformat() if evt.date_echeance_calculee else None,
        "date_declencheur": evt.date_declencheur.isoformat() if evt.date_declencheur else None,
        "duree_legale_jours": evt.duree_legale_jours,
        "critique": evt.critique,
        "palier_urgence": palier_urgence(evt),
        "statut_traitement": evt.statut_traitement,
        "statut_traitement_libelle": evt.get_statut_traitement_display(),
        "description": evt.description,
        "dossier_id": str(evt.dossier_id) if evt.dossier_id else None,
        "dossier_reference": getattr(evt.dossier, 'reference', None) if evt.dossier_id else None,
        # Nouveaux champs ManyToMany & ForeignKeys
        "responsables": [{"id": str(u.id), "nom": u.get_full_name() or u.username} for u in evt.responsables.all()],
        "parties_prenantes": [{"id": str(p.id), "nom": p.nom, "role": p.get_role_display()} for p in evt.parties_prenantes.all()],
        "tribunal_id": str(evt.tribunal_id) if evt.tribunal_id else None,
        "chambre_id": str(evt.chambre_id) if evt.chambre_id else None,
        "created_at": evt.created_at.strftime("%d/%m/%Y %H:%M") if evt.created_at else None,
    }

def _queryset_filtre(
    recherche="", type_evenement="", dossier_id="", critique="", 
    date_debut="", date_fin="", statut=""
):
    # Optimisation ORM : Evite le problème N+1 sur les relations
    qs = EvenementAgenda.objects.select_related(
        "dossier", "tribunal", "chambre"
    ).prefetch_related("responsables", "parties_prenantes").all()

    # 1. Recherche textuelle multi-critères
    if recherche:
        q_recherche = Q()
        for champ in CHAMPS_RECHERCHE:
            q_recherche |= Q(**{f"{champ}__icontains": recherche})
        qs = qs.filter(q_recherche)

    # 2. Filtres par type et statut procédural
    if type_evenement:
        qs = qs.filter(type=type_evenement)
    if statut:
        qs = qs.filter(statut_traitement=statut)
    if dossier_id:
        qs = qs.filter(dossier_id=dossier_id)
    if critique in ("true", "1", True):
        qs = qs.filter(critique=True)

    # 3. Filtrage temporel strict
    if date_debut:
        d_debut = _parse_date(date_debut)
        if d_debut:
            qs = qs.filter(date_heure__gte=datetime.combine(d_debut, time.min))
    if date_fin:
        d_fin = _parse_date(date_fin)
        if d_fin:
            qs = qs.filter(date_heure__lte=datetime.combine(d_fin, time.max))

    return qs.distinct()

def lister_evenements(request):
    recherche = request.GET.get('recherche', '').strip()
    type_evt = request.GET.get('type', '').strip()
    statut = request.GET.get('statut', '').strip()
    date_debut = request.GET.get('date_debut', '').strip()
    date_fin = request.GET.get('date_fin', '').strip()
    critique = request.GET.get('critique', '').strip()

    dossier_id = request.GET.get('dossier_id', '').strip()   # <- ligne à ajouter

    # select_related étendu à dossier__avocat_referent : nécessaire pour que le repli
    # sur l'avocat référent du dossier (si aucun responsable direct) ne déclenche pas
    # une requête SQL supplémentaire par ligne (N+1).
    queryset = EvenementAgenda.objects.select_related(
        'dossier', 'dossier__avocat_referent', 'tribunal', 'chambre'
    ).prefetch_related(
        'responsables', 'parties_prenantes', 'dossier__parties_prenantes'
    )
    if dossier_id:                                            # <- bloc à ajouter
            queryset = queryset.filter(dossier_id=dossier_id)
    
    if recherche:
        queryset = queryset.filter(
            Q(titre__icontains=recherche) |
            Q(description__icontains=recherche) |
            Q(dossier__intitule__icontains=recherche) |
            Q(dossier__reference__icontains=recherche)
        )
    if type_evt:
        queryset = queryset.filter(type=type_evt)
    if statut:
        queryset = queryset.filter(statut_traitement=statut)
    if date_debut:
        queryset = queryset.filter(date_heure__date__gte=date_debut)
    if date_fin:
        queryset = queryset.filter(date_heure__date__lte=date_fin)
    if critique.lower() in ['true', '1']:
        queryset = queryset.filter(critique=True)

    queryset = queryset.order_by('-date_heure')

    data = []
    for evt in queryset:
        # Repli sur l'avocat référent du dossier si aucun responsable direct n'est assigné
        responsables_directs = [
            f"{u.first_name} {u.last_name}".strip() or u.username
            for u in evt.responsables.all()
        ]
        responsables = responsables_directs or (
            [f"{evt.dossier.avocat_referent.first_name} {evt.dossier.avocat_referent.last_name}".strip()
             or evt.dossier.avocat_referent.username]
            if evt.dossier_id and evt.dossier.avocat_referent_id else []
        )

        """ parties_prenantes = [
            {
                "id": str(p.id),
                "nom": p.nom,
                "role": p.role,
                "role_display": ROLES_DICT.get(p.role, p.role),
                "telephone": getattr(p, 'telephone', '') or ''
            }
            for p in evt.parties_prenantes.all()
        ] """
        parties_directes = [_partie_prenante_vers_dict(p) for p in evt.parties_prenantes.all()]
        parties_prenantes = parties_directes or (
            [_partie_prenante_vers_dict(p) for p in evt.dossier.parties_prenantes.all()]
                if evt.dossier_id else []
            )

        dossier_detail = None
        if evt.dossier:
            dossier_detail = {
                'id': str(evt.dossier.id),
                'reference': getattr(evt.dossier, 'reference', ''),
                'intitule': getattr(evt.dossier, 'intitule', str(evt.dossier)),
            }

        data.append({
            'id': str(evt.id),
            'titre': evt.titre,
            'type': evt.type,
            'type_display': evt.get_type_display(),
            'type_delai': evt.type_delai,
            'type_delai_display': evt.get_type_delai_display() if evt.type_delai else None,

            'date_heure': evt.date_heure.isoformat() if evt.date_heure else None,
            'date_debut': evt.date_heure.isoformat() if evt.date_heure else None,
            'date_echeance_calculee': evt.date_echeance_calculee.isoformat() if evt.date_echeance_calculee else None,

            'statut': evt.statut_traitement,
            'statut_display': evt.get_statut_traitement_display(),
            'motif_renvoi': evt.motif_renvoi,
            'motif_renvoi_display': evt.get_motif_renvoi_display() if evt.motif_renvoi else None,
            'critique': evt.critique,

            'description': evt.description or '',
            'dossier_reference': evt.dossier.reference if (evt.dossier and getattr(evt.dossier, 'reference', None)) else (evt.dossier.intitule if evt.dossier else 'Hors dossier'),
            'dossier_detail': dossier_detail,

            'responsables': responsables,
            'parties_prenantes': parties_prenantes,

            'tribunal_nom': evt.tribunal.nom if evt.tribunal else None,
            'chambre_nom': evt.chambre.libelle if evt.chambre else None,
        })
    return {'resultats': data}


def _partie_prenante_vers_dict(p):
    return {
        "id": str(p.id),
        "nom": p.nom,
        "role": p.role,
        "role_display": ROLES_DICT.get(p.role, p.role),
        "telephone": getattr(p, 'telephone', '') or ''
    }


def obtenir_evenement(evenement_id) -> EvenementAgenda:
    return EvenementAgenda.objects.select_related("dossier").get(pk=evenement_id)

""" def creer_evenement(payload: dict, utilisateur) -> EvenementAgenda:
    _valider_payload(payload)
    evt = EvenementAgenda(
        titre=payload["titre"],
        type=payload.get("type", "autre"),
        type_delai=payload.get("type_delai") or None,
        date_heure=payload["date_heure"],
        date_declencheur=payload.get("date_declencheur") or None,
        duree_legale_jours=payload.get("duree_legale_jours") or None,
        critique=str(payload.get("critique", False)).lower() in ("true", "1"),
        statut_traitement=payload.get("statut_traitement", "en_attente"),
        description=payload.get("description") or None,
        dossier_id=payload.get("dossier_id") or None,
        tribunal_id=payload.get("tribunal_id") or None,
        chambre_id=payload.get("chambre_id") or None,
        created_by=utilisateur,
    )
    evt.full_clean()
    evt.save()  # Création en BDD requise avant d'affecter les M2M

    # Gestion des ManyToMany
    if "responsables" in payload:
        evt.responsables.set(payload["responsables"])
    if "parties_prenantes" in payload:
        evt.parties_prenantes.set(payload["parties_prenantes"])

    return evt """


@transaction.atomic
def creer_evenement(payload: dict, utilisateur) -> EvenementAgenda:
    _valider_payload(payload)
    
    # 1. Instanciation et sauvegarde de l'événement de base
    evt = EvenementAgenda(
        titre=payload["titre"],
        type=payload.get("type", "autre"),
        type_delai=payload.get("type_delai") or None,
        date_heure=payload["date_heure"],
        date_declencheur=payload.get("date_declencheur") or None,
        duree_legale_jours=payload.get("duree_legale_jours") or None,
        critique=str(payload.get("critique", False)).lower() in ("true", "1"),
        statut_traitement=payload.get("statut_traitement", "en_attente"),
        description=payload.get("description") or None,
        dossier_id=payload.get("dossier_id") or None,
        tribunal_id=payload.get("tribunal_id") or None,
        chambre_id=payload.get("chambre_id") or None,
        created_by=utilisateur,
    )
    evt.full_clean()
    evt.save()

    # 2. Affectation des Avocats / Collaborateurs internes (responsables)
    if "responsables" in payload and payload["responsables"]:
        evt.responsables.set(payload["responsables"])

    # 3. FUSION ET ENREGISTREMENT DES PARTIES PRENANTES
    liste_ids_finales = set()

    # A. Héritage automatique des parties prenantes déjà présentes dans le dossier lié
    if evt.dossier_id:
        parties_existantes_dossier = PartiePrenante.objects.filter(dossier_id=evt.dossier_id)
        for pp in parties_existantes_dossier:
            liste_ids_finales.add(str(pp.id))

    # B. 🌟 ENREGISTREMENT PHYSIQUE DES NOUVELLES PP DE L'AGENDA EN BDD
    if "nouvelles_parties_prenantes" in payload and payload["nouvelles_parties_prenantes"]:
        for nv_pp in payload["nouvelles_parties_prenantes"]:
            if nv_pp.get("nom") and nv_pp.get("role"):
                # Création réelle et étanche : dossier=None détache ce profil de l'affaire globale
                nouvelle_pp_isolee = PartiePrenante.objects.create(
                    dossier=None,  # Garantit que ce profil n'apparaîtra jamais dans la fiche fixe du dossier
                    nom=nv_pp["nom"].strip(),
                    role=nv_pp["role"].strip(),
                    notes=f"[EVENEMENT_ONLY] Créé spécifiquement pour l'audience : {evt.titre}",
                    created_by=utilisateur
                )
                # On insère le véritable UUID généré par la BDD dans notre liste
                liste_ids_finales.add(str(nouvelle_pp_isolee.id))

    # C. Récupération des anciennes parties prenantes cochées manuellement à l'écran
    if "parties_prenantes" in payload and payload["parties_prenantes"]:
        for pp_id in payload["parties_prenantes"]:
            if pp_id:
                liste_ids_finales.add(str(pp_id))

    # D. Écriture finale dans la table ManyToMany de l'événement
    if liste_ids_finales:
        evt.parties_prenantes.set(list(liste_ids_finales))

     # ─── CODE DE DEBUGGING À AJOUTER ──────────────────────────────────
    print("\n" + "="*50)
    print(f"🌟 ÉVÉNEMENT CRÉÉ AVEC SUCCÈS (ID: {evt.id})")
    print(f"Titre: {evt.titre} | Statut: {evt.statut_traitement}")
    print(f"Créé par: {evt.created_by}")
    
    # Récupération des relations M2M
    responsables = list(evt.responsables.values_list('username', flat=True)) # Ajustez le champ (ex: 'email' ou 'nom')
    parties = list(evt.parties_prenantes.values('id', 'nom', 'role'))
    
    print(f"Responsables ({len(responsables)}): {responsables}")
    print(f"Parties Prenantes ({len(parties)}):")
    for p in parties:
        print(f"  - [{p['role']}] {p['nom']} (ID: {p['id']})")
    print("="*50 + "\n")
    # ─────────────────────────────────────────────────────────────────
    
    return evt

""" 
def modifier_evenement(evenement_id, payload: dict, utilisateur) -> EvenementAgenda:
    _valider_payload(payload)
    evt = obtenir_evenement(evenement_id)
    evt.titre = payload.get("titre", evt.titre)
    evt.type = payload.get("type", evt.type)
    evt.type_delai = payload.get("type_delai") or None
    evt.date_heure = payload.get("date_heure", evt.date_heure)
    evt.date_declencheur = payload.get("date_declencheur") or None
    evt.duree_legale_jours = payload.get("duree_legale_jours") or None
    evt.critique = str(payload.get("critique", evt.critique)).lower() in ("true", "1")
    evt.statut_traitement = payload.get("statut_traitement", evt.statut_traitement)
    evt.description = payload.get("description") or None
    evt.dossier_id = payload.get("dossier_id") or None
    evt.tribunal_id = payload.get("tribunal_id") or None
    evt.chambre_id = payload.get("chambre_id") or None
    evt.edited_by = utilisateur

    evt.full_clean()
    evt.save()

    # Mise à jour des ManyToMany
    if "responsables" in payload:
        evt.responsables.set(payload["responsables"])
    if "parties_prenantes" in payload:
        evt.parties_prenantes.set(payload["parties_prenantes"])

    return evt """

@transaction.atomic
def modifier_evenement_agenda(event_id, payload: dict, utilisateur) -> EvenementAgenda:
    evt = get_object_or_404(EvenementAgenda, pk=event_id)

    # Mise à jour des attributs principaux
    evt.titre = payload.get('titre', evt.titre)
    evt.type = payload.get('type', evt.type)
    evt.statut_traitement = payload.get('statut_traitement', evt.statut_traitement)
    evt.description = payload.get('description', evt.description)
    evt.critique = bool(payload.get('critique', evt.critique))
    evt.edited_by = utilisateur
    # Gestion de la clé étrangère Dossier
    dossier_id = payload.get('dossier')
    evt.dossier_id = dossier_id if dossier_id else None

    if payload.get('date_heure'):
        evt.date_heure = payload['date_heure']

    # Délais de procédure
    evt.type_delai = payload.get('type_delai') or None
    evt.date_declencheur = payload.get('date_declencheur') or None
    evt.duree_legale_jours = payload.get('duree_legale_jours') or None

    evt.save()

    # 1. Mise à jour de la M2M Responsables (Avocats / Collaborateurs)
    if 'responsables' in payload:
        evt.responsables.set(payload['responsables'])

    # 2. Mise à jour de la M2M Parties Prenantes (Sécurisée selon le dossier)
    if 'parties_prenantes' in payload:
        pps = payload['parties_prenantes']
        if evt.dossier_id:
            # Sécurité procédurale : filtrer les parties prenantes qui appartiennent au dossier
            pps_valides = PartiePrenante.objects.filter(id__in=pps, dossier_id=evt.dossier_id)
            evt.parties_prenantes.set(pps_valides)
        else:
            evt.parties_prenantes.clear()

    return evt

""" def modifier_evenement(evenement_id, payload: dict, utilisateur) -> EvenementAgenda:
    _valider_payload(payload)
    evt = get_object_or_404(EvenementAgenda, id=evenement_id)
    
    # 1. Mise à jour des champs classiques
    evt.titre = payload.get("titre", evt.titre)
    evt.date_heure = payload.get("date_heure", evt.date_heure)
    evt.statut_traitement = payload.get("statut_traitement", evt.statut_traitement)
    evt.description = payload.get("description", evt.description)
    evt.edited_by = utilisateur
    evt.save()

    # 2. Mise à jour des responsables internes
    if "responsables" in payload:
        evt.responsables.set(payload["responsables"])

    # 3. MISE À JOUR DES PARTIES PRENANTES DE CETTE AUDIENCE
    if "parties_prenantes" in payload:
        liste_ids_modification = set(payload["parties_prenantes"])
        
        # 🌟 SÉCURITÉ MÉTIER : On force la ré-inclusion des PP permanentes du dossier
        # pour éviter qu'un avocat ne les décoche par erreur sur cette audience.
        if evt.dossier_id:
            parties_dossier = PartiePrenante.objects.filter(dossier_id=evt.dossier_id).exclude(notes__startswith="[EVENEMENT_ONLY]")
            for pp in parties_dossier:
                liste_ids_modification.add(str(pp.id))
                
        # On applique le nouveau jeu d'intervenants à l'audience
        evt.parties_prenantes.set(list(liste_ids_modification))

    return evt """


def supprimer_evenement(evenement_id):
    obtenir_evenement(evenement_id).delete()


def options_dossiers():
    return [
        {"id": str(d.id), "label": f"{d.reference} — {d.intitule}"}
        #for d in Dossier.objects.all().order_by("-date_ouverture")[:500] 
        for d in Dossier.objects.all().order_by("-created_at")[:500] 
    ]



def _valider_payload(payload: dict):
    if not payload.get("titre"):
        raise ValidationError("Le titre de l'événement est obligatoire.")
    if not payload.get("date_heure"):
        raise ValidationError("La date/heure de l'événement est obligatoire.")


def _parse_date(valeur: str):
    return datetime.strptime(valeur, "%Y-%m-%d").date()
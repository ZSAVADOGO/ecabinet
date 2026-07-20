/**
 * Gestionnaire Global et Sécurisé des Modals - eCabinet
 */

/* const eCabinetModals = {
    // Fonction principale pour ouvrir n'importe quel modal par son ID HTML
    ouvrir(modalId, entiteId = null) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`eCabinet [Erreur] : Le modal avec l'ID "${modalId}" n'existe pas.`);
            return;
        }

        // Si un ID d'entité (ex: ID d'un client à modifier) est passé, on l'injecte dans le formulaire caché
        if (entiteId) {
            const inputId = modal.querySelector('.modal-entite-id');
            if (inputId) inputId.value = entiteId;
        }

        // Activation visuelle via les classes Tailwind CSS (retire 'hidden', applique l'affichage flex)
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        
        // Bloque le défilement de la page principale en arrière-plan pour le confort UX
        document.body.classList.add('overflow-hidden');
    },

    // Fonction pour fermer un modal spécifique
    fermer(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('flex');
            modal.classList.add('hidden');
            document.body.classList.remove('overflow-hidden');
        }
    }
};

// Exposition de l'objet à la fenêtre globale du navigateur pour vos templates HTML
window.ouvrirModal = eCabinetModals.ouvrir;
window.fermerModal = eCabinetModals.fermer;

// Écouteur de sécurité : Fermeture automatique si clic sur l'arrière-plan flouté
document.addEventListener('DOMContentLoaded', () => {
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (evenement) => {
            // Si l'utilisateur clique strictement sur le fond et pas sur la boîte blanche interne
            if (evenement.target === overlay) {
                eCabinetModals.fermer(overlay.id);
            }
        });
    });
    console.log("⚙️ eCabinet : Le gestionnaire de fenêtres surgissantes (Modals) est prêt.");
});
*/

/**
 * Gestionnaire Global et Sécurisé des Modals - eCabinet
 * ------------------------------------------------------
 * Corrections apportées (v2) :
 *  - `ouvrir()` accepte désormais un objet `data` complet (pas seulement un ID)
 *    pour préremplir TOUS les champs d'un formulaire d'édition
 *    (ex: Client -> nom, prenom, raison_sociale, ifu_rccm, telephone1, telephone2...
 *     Dossier -> reference, intitule, type_affaire, statut, client_id, avocat_referent_id...)
 *  - Reset automatique du formulaire à l'ouverture en mode "création" (data absent)
 *    pour éviter qu'un modal réutilisé garde les valeurs d'une édition précédente.
 *  - Fermeture au clavier (touche Échap) en plus du clic sur l'overlay.
 *  - Focus automatique sur le premier champ du modal (accessibilité).
 *  - Verrouillage anti-bug : gère plusieurs modals ouverts/fermés successivement
 *    sans laisser `overflow-hidden` bloqué sur le body.
 */

function sortTable(th) {
    const table = th.closest('table');
    const tbody = table.querySelector('tbody');
    const ths = [...th.parentElement.children];
    const idx = ths.indexOf(th);
    const asc = th.dataset.order !== 'asc';
    ths.forEach(h => { h.dataset.order = ''; const a = h.querySelector('.sort-arrow'); if (a) a.textContent = '↕'; });
    th.dataset.order = asc ? 'asc' : 'desc';
    const arrow = th.querySelector('.sort-arrow'); if (arrow) arrow.textContent = asc ? '↑' : '↓';
    const type = th.dataset.type || 'text';
    const rows = [...tbody.querySelectorAll('tr')];
    rows.sort((a, b) => {
        let x = a.children[idx]?.dataset.sort ?? a.children[idx]?.textContent.trim() ?? '';
        let y = b.children[idx]?.dataset.sort ?? b.children[idx]?.textContent.trim() ?? '';
        if (type === 'number') { x = parseFloat(x.replace(/[^0-9.-]/g, '')) || 0; y = parseFloat(y.replace(/[^0-9.-]/g, '')) || 0; }
        else if (type === 'date') {
    x = new Date(x.replace(' ', 'T')).getTime() || 0;
    y = new Date(y.replace(' ', 'T')).getTime() || 0;
}
        return (x > y ? 1 : x < y ? -1 : 0) * (asc ? 1 : -1);
    });
    rows.forEach(r => tbody.appendChild(r));
}

/*async function envoyerFormulaire(url, payload) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) { Swal.fire('Succès', data.message || 'Enregistré avec succès.', 'success').then(() => location.href = data.redirect || '/'); }
    else { Swal.fire('Erreur', data.error || 'Une erreur est survenue.', 'error'); }
}*/
async function envoyerFormulaire(url, payload) {
    console.log("Envoi du formulaire vers l'URL :", url, "avec le payload :", payload);
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify(payload)
        });

        // 1. On récupère d'abord le texte brut de la réponse
        const texteBrut = await res.text();
        let data = {};
            
        console.log("TesteBrut :", texteBrut, "data init:", data );

        
        try {
            // 2. On tente de le transformer en JSON
            data = JSON.parse(texteBrut);
            console.log("Nouveau data = JSON.parse(texteBrut):", data );
        } catch (e) {
            // Si ce n'est pas du JSON, c'est du HTML de crash Django !
            console.error("Le serveur a renvoyé du HTML au lieu de JSON. Contenu :", texteBrut);
            Swal.fire('Erreur 500', 'Le serveur Django a planté (consultez la console Python).', 'error');
            return;
        }

        if (res.ok) { 
            Swal.fire('Succès', data.message || 'Enregistré avec succès.', 'success')
                .then(() => location.href = data.redirect || '/'); 
        } else { 
            Swal.fire('Erreur', data.erreur || data.error || 'Une erreur est survenue.', 'error'); 
        }
    } catch (erreurReseau) {
        console.error("Erreur réseau ou JavaScript :", erreurReseau);
    }
}


function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
}

const eCabinetModals = {
    _pileModalsOuverts: [],

    /**
     * Ouvre un modal par son ID HTML.
     * @param {string} modalId - ID du modal à ouvrir.
     * @param {Object|string|null} data - Soit un objet complet à injecter dans le
     *        formulaire (mode édition), soit directement un ID d'entité (rétro-compatibilité),
     *        soit null (mode création -> le formulaire est réinitialisé).
     */
    ouvrir(modalId, data = null) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`eCabinet [Erreur] : Le modal avec l'ID "${modalId}" n'existe pas.`);
            return;
        }

        const form = modal.querySelector('form');

        if (data && typeof data === 'object') {
            // Mode édition : on injecte chaque paire clé/valeur dans les champs correspondants
            this._remplirFormulaire(modal, data);
        } else if (data) {
            // Rétro-compatibilité : un simple ID d'entité était passé (ancien comportement)
            const inputId = modal.querySelector('.modal-entite-id');
            if (inputId) inputId.value = data;
        } else if (form) {
            // Mode création : formulaire vierge
            form.reset();
            const inputId = modal.querySelector('.modal-entite-id');
            if (inputId) inputId.value = '';
        }

        modal.classList.remove('hidden');
        modal.classList.add('flex');
        document.body.classList.add('overflow-hidden');
        this._pileModalsOuverts.push(modalId);

        // Accessibilité : focus sur le premier champ saisissable
        const premierChamp = modal.querySelector('input:not([type="hidden"]), select, textarea');
        if (premierChamp) setTimeout(() => premierChamp.focus(), 50);
    },

    /**
     * Remplit récursivement les champs d'un formulaire à partir d'un objet de données.
     * Cherche les éléments par [name="clé"], à défaut par .modal-champ-clé.
     */
    _remplirFormulaire(modal, data) {
        Object.entries(data).forEach(([cle, valeur]) => {
            const champ = modal.querySelector(`[name="${cle}"]`);
            if (!champ) return;

            if (champ.type === 'checkbox') {
                champ.checked = Boolean(valeur);
            } else {
                champ.value = valeur ?? '';
            }
        });
    },

    // Fonction pour fermer un modal spécifique
    fermer(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('flex');
            modal.classList.add('hidden');
        }
        this._pileModalsOuverts = this._pileModalsOuverts.filter(id => id !== modalId);
        if (this._pileModalsOuverts.length === 0) {
            document.body.classList.remove('overflow-hidden');
        }
    },

    // Ferme le modal actif au sommet de la pile (utilisé par la touche Échap)
    fermerDernier() {
        const dernier = this._pileModalsOuverts[this._pileModalsOuverts.length - 1];
        if (dernier) this.fermer(dernier);
    },

    /**
     * Sérialise un formulaire en objet JS simple, prêt à être envoyé en JSON
     * (utile pour les appels fetch() vers les endpoints Django).
     */
    serialiser(formulaire) {
        const formData = new FormData(formulaire);
        const objet = {};
        formData.forEach((valeur, cle) => {
            objet[cle] = valeur;
        });
        return objet;
    }
};

// Exposition de l'objet à la fenêtre globale du navigateur pour vos templates HTML
window.ouvrirModal = (modalId, data) => eCabinetModals.ouvrir(modalId, data);
window.fermerModal = (modalId) => eCabinetModals.fermer(modalId);
window.eCabinetModals = eCabinetModals;

// Écouteurs de sécurité : fermeture automatique (clic overlay + touche Échap)
document.addEventListener('DOMContentLoaded', () => {
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (evenement) => {
            if (evenement.target === overlay) {
                eCabinetModals.fermer(overlay.id);
            }
        });
    });

    document.addEventListener('keydown', (evenement) => {
        if (evenement.key === 'Escape') {
            eCabinetModals.fermerDernier();
        }
    });

    console.log("⚙️ eCabinet : Le gestionnaire de fenêtres surgissantes (Modals) est prêt.");
});
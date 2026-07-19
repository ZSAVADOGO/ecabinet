/*const eCabinetAlerts = {
    // Notification de succès (ex: Enregistrement client réussi)
    succes(message, titre = "Opération réussie") {
        Swal.fire({
            title: titre,
            text: message,
            icon: "success",
            confirmButtonColor: "#4f46e5", // Indigo-600 correspondant à l'UI
            confirmButtonText: "Continuer"
        });
    },

    // Notification d'erreur ou d'échec
    erreur(message, titre = "Une erreur est survenue") {
        Swal.fire({
            title: titre,
            text: message,
            icon: "error",
            confirmButtonColor: "#4f46e5"
        });
    },

    // Boîte de dialogue de confirmation critique (ex: Alerte suppression de dossier)
    confirmerSuppression(message, actionCallback) {
        Swal.fire({
            title: "Êtes-vous sûr ?",
            text: message || "Cette action est irréversible et sera journalisée dans l'audit de conformité.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#dc2626", // Rouge Danger
            cancelButtonColor: "#4b5563",  // Gris Neutre
            confirmButtonText: "Oui, supprimer",
            cancelButtonText: "Annuler"
        }).then((result) => {
            if (result.isConfirmed && typeof actionCallback === "function") {
                actionCallback();
            }
        });
    }
};

// Rend l'objet d'alertes de base accessible globalement
window.eCabinetAlerts = eCabinetAlerts;*/

/**
 * Gestionnaire Global des Alertes - eCabinet
 * -------------------------------------------
 * Corrections apportées (v2) :
 *  - `chargement()` / `fermerChargement()` : indispensable pour les appels fetch()
 *    du dashboard (recherche, pagination, création/édition/suppression en AJAX).
 *  - `toast()` : notification discrète (ex: "Filtre appliqué") sans bloquer l'UI.
 *  - `confirmer()` générique dont `confirmerSuppression()` n'est plus qu'un cas particulier
 *    (évite la duplication de code, plus facile à étendre pour d'autres confirmations
 *    comme "clore un dossier" ou "archiver un client").
 */

const eCabinetAlerts = {
    // Notification de succès (ex: Enregistrement client réussi)
    succes(message, titre = "Opération réussie") {
        return Swal.fire({
            title: titre,
            text: message,
            icon: "success",
            confirmButtonColor: "#4f46e5", // Indigo-600 correspondant à l'UI
            confirmButtonText: "Continuer"
        });
    },

    // Notification d'erreur ou d'échec
    erreur(message, titre = "Une erreur est survenue") {
        return Swal.fire({
            title: titre,
            text: message,
            icon: "error",
            confirmButtonColor: "#4f46e5"
        });
    },

    // Toast discret, auto-fermé, pour les actions mineures (filtre, page changée, etc.)
    toast(message, icon = "success") {
        return Swal.fire({
            toast: true,
            position: "top-end",
            icon,
            title: message,
            showConfirmButton: false,
            timer: 2500,
            timerProgressBar: true,
        });
    },

    // Spinner bloquant pendant un appel AJAX (recherche, sauvegarde...)
    chargement(message = "Veuillez patienter...") {
        Swal.fire({
            title: message,
            allowOutsideClick: false,
            allowEscapeKey: false,
            didOpen: () => Swal.showLoading(),
        });
    },

    fermerChargement() {
        Swal.close();
    },

    // Confirmation générique réutilisable
    confirmer({
        titre = "Êtes-vous sûr ?",
        message = "Cette action est irréversible.",
        icon = "warning",
        confirmButtonText = "Confirmer",
        confirmButtonColor = "#4f46e5",
    } = {}, actionCallback) {
        return Swal.fire({
            title: titre,
            text: message,
            icon,
            showCancelButton: true,
            confirmButtonColor,
            cancelButtonColor: "#4b5563",
            confirmButtonText,
            cancelButtonText: "Annuler",
        }).then((result) => {
            if (result.isConfirmed && typeof actionCallback === "function") {
                actionCallback();
            }
            return result;
        });
    },

    // Boîte de dialogue de confirmation critique (ex: suppression client/dossier)
    confirmerSuppression(message, actionCallback) {
        return this.confirmer({
            titre: "Êtes-vous sûr ?",
            message: message || "Cette action est irréversible et sera journalisée dans l'audit de conformité.",
            icon: "warning",
            confirmButtonText: "Oui, supprimer",
            confirmButtonColor: "#dc2626", // Rouge Danger
        }, actionCallback);
    }
};

// Rend l'objet d'alertes accessible globalement
window.eCabinetAlerts = eCabinetAlerts;
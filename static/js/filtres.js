/**
 * Module générique de gestion des filtres :
 * - Bouton croix pour vider un champ (input/select) marqué [data-clearable]
 * - Bouton reset visible si au moins un champ [data-reset-group] est rempli
 *
 * Utilisable sur N'IMPORTE QUEL module, sans JS supplémentaire.
 * Il suffit d'ajouter les bons data-attributes dans le HTML.
 */
(function () {
    function toggleClearBtn(wrapper) {
        const input = wrapper.querySelector('input,select');
        const btn = wrapper.querySelector('[data-clear-btn]');
        if (input && btn) btn.classList.toggle('hidden', !input.value);
    }

    function toggleResetGroup(group) {
        const fields = document.querySelectorAll(`[data-reset-group="${group}"]`);
        const resetBtn = document.querySelector(`[data-reset-btn="${group}"]`);
        if (!resetBtn) return;
        const actif = [...fields].some(f => f.value);
        resetBtn.classList.toggle('hidden', !actif);
    }

    // Déclenche input + change, pour être compatible avec toute fonction de filtrage existante
    function notifyFieldChange(el) {
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    document.addEventListener('input', e => {
        const wrapper = e.target.closest('[data-clearable]');
        if (wrapper) toggleClearBtn(wrapper);

        const group = e.target.dataset.resetGroup;
        if (group) toggleResetGroup(group);
    });

    document.addEventListener('click', e => {
        const btn = e.target.closest('[data-clear-btn]');
        if (!btn) return;
        const input = btn.closest('[data-clearable]').querySelector('input,select');
        input.value = '';
        notifyFieldChange(input);
    });

    window.reinitialiserGroupe = function (group) {
        document.querySelectorAll(`[data-reset-group="${group}"]`).forEach(el => {
            el.value = '';
            notifyFieldChange(el);
        });
    };
})();

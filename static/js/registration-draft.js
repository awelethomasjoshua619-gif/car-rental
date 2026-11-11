(() => {
    const draftKey = 'fastcars.registration-draft.v1';

    document.addEventListener('DOMContentLoaded', () => {
        const form = document.querySelector('form[data-preserve-draft="registration"]');
        if (!form) return;

        let saved = {};
        try {
            saved = JSON.parse(sessionStorage.getItem(draftKey) || '{}');
        } catch (_) {
            sessionStorage.removeItem(draftKey);
        }

        for (const field of form.elements) {
            if (!field.name || field.name === 'csrf_token' || !(field.name in saved)) continue;
            if (field.type === 'checkbox' || field.type === 'radio') {
                field.checked = Boolean(saved[field.name]);
            } else {
                field.value = saved[field.name];
            }
        }

        const saveDraft = () => {
            const draft = {};
            for (const field of form.elements) {
                if (!field.name || field.name === 'csrf_token' || field.type === 'hidden' || field.type === 'submit' || field.type === 'button') continue;
                draft[field.name] = (field.type === 'checkbox' || field.type === 'radio') ? field.checked : field.value;
            }
            try {
                sessionStorage.setItem(draftKey, JSON.stringify(draft));
            } catch (_) {
                // The form remains usable when browser storage is unavailable.
            }
        };

        form.addEventListener('input', saveDraft);
        form.addEventListener('change', saveDraft);
        window.addEventListener('pagehide', saveDraft);
    });
})();

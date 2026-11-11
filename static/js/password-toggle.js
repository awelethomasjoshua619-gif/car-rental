document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="password"]').forEach((field) => {
        const parent = field.parentElement;
        const inInputGroup = parent && parent.classList.contains('input-group');
        let wrapper = parent;

        if (!inInputGroup) {
            wrapper = document.createElement('div');
            wrapper.className = 'password-field-wrap';
            field.parentNode.insertBefore(wrapper, field);
            wrapper.appendChild(field);
        } else {
            wrapper.classList.add('password-field-wrap');
        }

        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'password-visibility-toggle';
        toggle.setAttribute('aria-label', 'Show password');
        toggle.setAttribute('aria-pressed', 'false');
        toggle.setAttribute('title', 'Show password');
        toggle.innerHTML = '<i class="fa-solid fa-eye" aria-hidden="true"></i>';
        field.classList.add('password-visibility-input');
        wrapper.appendChild(toggle);

        toggle.addEventListener('click', () => {
            const showPassword = field.type === 'password';
            field.type = showPassword ? 'text' : 'password';
            toggle.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
            toggle.setAttribute('title', showPassword ? 'Hide password' : 'Show password');
            toggle.setAttribute('aria-pressed', String(showPassword));
            toggle.innerHTML = `<i class="fa-solid ${showPassword ? 'fa-eye-slash' : 'fa-eye'}" aria-hidden="true"></i>`;
            field.focus();
        });
    });
});

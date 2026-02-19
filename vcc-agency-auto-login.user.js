// ==UserScript==
// @name         VCC Agency Auto Login
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Auto-fill username and password, check "Remember this Device", and login
// @author       el739
// @match        https://vcc.agency/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Configure your credentials here
    const USERNAME = 'your_username_here';
    const PASSWORD = 'your_password_here';

    window.addEventListener('load', function() {
        setTimeout(() => {
            const usernameInput = document.getElementById('input-1');
            const passwordInput = document.getElementById('input-3');
            const rememberCheckbox = document.getElementById('checkbox-5');
            const signInButton = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Sign In'));

            if (usernameInput && passwordInput && rememberCheckbox && signInButton) {
                usernameInput.value = USERNAME;
                usernameInput.dispatchEvent(new Event('input', { bubbles: true }));

                passwordInput.value = PASSWORD;
                passwordInput.dispatchEvent(new Event('input', { bubbles: true }));

                if (!rememberCheckbox.checked) {
                    rememberCheckbox.click();
                }
                setTimeout(() => {
                    signInButton.click();
                }, 500);
            }
        }, 1000);
    });
})();

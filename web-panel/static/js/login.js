/**
 * Login Page Logic
 */

document.addEventListener('DOMContentLoaded', function() {
    const loginBtn = document.getElementById('loginBtn');
    const tokenInput = document.getElementById('token');
    const errorMsg = document.getElementById('errorMsg');

    // Check if already authenticated
    if (Storage.isAuthenticated()) {
        window.location.href = '/dashboard.html';
        return;
    }

    // Handle login button click
    loginBtn.addEventListener('click', handleLogin);

    // Handle Enter key
    tokenInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleLogin();
        }
    });

    // Focus token input
    tokenInput.focus();

    async function handleLogin() {
        const token = tokenInput.value.trim().toUpperCase();

        if (!token) {
            showError('Введите код из бота');
            return;
        }

        // Show loading state
        loginBtn.disabled = true;
        loginBtn.innerHTML = '<span class="spinner"></span> Вход...';
        hideError();

        try {
            const response = await AuthAPI.login(token);

            if (response.success) {
                // Save token and master_id
                Storage.setToken(token);
                Storage.setMasterId(response.master_id);

                // Redirect to dashboard
                window.location.href = '/dashboard.html';
            } else {
                showError(response.message || 'Ошибка входа');
            }
        } catch (error) {
            showError(error.message || 'Ошибка соединения с сервером');
        } finally {
            // Reset button state
            loginBtn.disabled = false;
            loginBtn.innerHTML = 'Войти';
        }
    }

    function showError(message) {
        errorMsg.textContent = message;
        errorMsg.style.display = 'block';
    }

    function hideError() {
        errorMsg.style.display = 'none';
    }
});

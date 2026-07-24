// static/js/chat-logic/auth.js

// ============================================================
// AUTENTICACIÓN CON TOKEN
// ============================================================

function getToken() {
    return localStorage.getItem('access_token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function isAuthenticated() {
    return !!getToken();
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login/';
}

// ============================================================
// OBTENER USUARIO ACTUAL
// ============================================================

async function fetchCurrentUser() {
    try {
        const token = getToken();
        if (!token) {
 console.warn('No hay token');
            return null;
        }
        
        const response = await fetch('/api/accounts/me/', {
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.status === 404) {
 console.warn('Endpoint /api/accounts/me/ no encontrado, continuando sin usuario');
            //  No fallar, solo continuar
            return null;
        }
        
        if (!response.ok) {
            if (response.status === 401) {
                const refreshed = await refreshToken();
                if (refreshed) {
                    return fetchCurrentUser();
                } else {
                    logout();
                    return null;
                }
            }
            throw new Error('Error al obtener usuario');
        }
        
        const data = await response.json();
 console.log('Usuario actual:', data);
        return data;
    } catch (error) {
 console.warn('No se pudo obtener el usuario:', error.message);
        return null;
    }
}

// ============================================================
// VERIFICAR AUTENTICACIÓN AL CARGAR
// ============================================================

(function checkAuth() {
    const token = getToken();
    if (token) {
 console.log('Token encontrado en localStorage');
    } else {
 console.log('No hay token en localStorage');
    }
})();

// ============================================================
// EXPONER FUNCIONES GLOBALES
// ============================================================

window.getToken = getToken;
window.getRefreshToken = getRefreshToken;
window.isAuthenticated = isAuthenticated;
window.logout = logout;
window.fetchCurrentUser = fetchCurrentUser;

console.log('Auth cargado');
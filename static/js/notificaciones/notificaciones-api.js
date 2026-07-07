// ============================================================
// NOTIFICATIONS API - Llamadas al backend
// ============================================================

function getToken() {
    return localStorage.getItem('access_token');
}

function getHeaders() {
    const token = getToken();
    return {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    };
}

async function fetchNotifications() {
    const response = await fetch('/api/notifications/?limit=100', {
        headers: getHeaders()
    });
    
    if (!response.ok) {
        throw new Error('Error al cargar notificaciones');
    }
    
    return await response.json();
}

async function markNotificationAsRead(notificationId) {
    const response = await fetch(`/api/notifications/${notificationId}/read/`, {
        method: 'PATCH',
        headers: getHeaders()
    });
    
    if (!response.ok) {
        throw new Error('Error al marcar como leída');
    }
    
    return await response.json();
}

async function markAllNotificationsAsRead() {
    const response = await fetch('/api/notifications/mark-read/', {
        method: 'PATCH',
        headers: getHeaders(),
        body: JSON.stringify({ mark_all: true })
    });
    
    if (!response.ok) {
        throw new Error('Error al marcar todas como leídas');
    }
    
    return await response.json();
}

async function deleteNotification(notificationId) {
    const response = await fetch(`/api/notifications/${notificationId}/`, {
        method: 'DELETE',
        headers: getHeaders()
    });
    
    if (!response.ok) {
        throw new Error('Error al eliminar notificación');
    }
    
    return true;
}
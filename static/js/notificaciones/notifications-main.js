// ============================================================
// NOTIFICATIONS MAIN - Punto de entrada e inicialización
// ============================================================

// Exponer funciones globales para los onclick del HTML
window.markAsRead = async function(notificationId) {
    try {
        await markNotificationAsRead(notificationId);
        await loadNotifications();
    } catch (error) {
        console.error('Error al marcar como leída:', error);
    }
};

window.markAllAsRead = async function() {
    try {
        await markAllNotificationsAsRead();
        await loadNotifications();
    } catch (error) {
        console.error('Error al marcar todas como leídas:', error);
    }
};

window.deleteNotification = async function(notificationId) {
    if (!confirm('¿Eliminar esta notificación?')) {
        return;
    }

    try {
        await deleteNotification(notificationId);
        await loadNotifications();
    } catch (error) {
        console.error('Error al eliminar notificación:', error);
    }
};

async function loadNotifications() {
    try {
        showLoading();
        
        const data = await fetchNotifications();
        const notifications = data.notifications || [];
        const unreadCount = data.unread_count || 0;
        
        renderNotifications(notifications, unreadCount);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'Intenta recargar la página');
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadNotifications();
    
    // Recargar cada 10 segundos
    setInterval(loadNotifications, 10000);
});
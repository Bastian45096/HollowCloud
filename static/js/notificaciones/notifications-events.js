// ============================================================
// NOTIFICATIONS EVENTS - Event listeners y handlers
// ============================================================

function setupEventListeners() {
    // Botón "Marcar todas como leídas"
    const markAllBtn = document.getElementById('markAllReadBtn');
    if (markAllBtn) {
        markAllBtn.addEventListener('click', async function() {
            try {
                await window.markAllAsRead();
                await loadNotifications();
            } catch (error) {
                console.error('Error al marcar todas como leídas:', error);
            }
        });
    }
}
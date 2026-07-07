// static/js/notifications-ui.js

// ============================================================
// NOTIFICATIONS UI - Renderizado y manipulación del DOM
// ============================================================

function getTimeAgo(dateString) {
    const now = new Date();
    const date = new Date(dateString);
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'ahora mismo';
    if (diff < 3600) return `hace ${Math.floor(diff / 60)} minuto${Math.floor(diff / 60) > 1 ? 's' : ''}`;
    if (diff < 86400) return `hace ${Math.floor(diff / 3600)} hora${Math.floor(diff / 3600) > 1 ? 's' : ''}`;
    if (diff < 2592000) return `hace ${Math.floor(diff / 86400)} día${Math.floor(diff / 86400) > 1 ? 's' : ''}`;
    return date.toLocaleDateString();
}

// ============================================================
// ICONOS PERSONALIZADOS
// ============================================================

function getNotificationIcon(type, extraData = {}) {
    // 🔥 SI ES ABANDONO DE WORKSPACE
    if (extraData && extraData.type === 'user_left_workspace') {
        return `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 28px; height: 28px; display: block; flex-shrink: 0;">
                <defs>
                    <linearGradient id="leaveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#E95420"/>
                        <stop offset="100%" style="stop-color:#77216F"/>
                    </linearGradient>
                </defs>
                
                <!-- Círculo de fondo -->
                <circle cx="12" cy="12" r="11" fill="#2C2C2C" opacity="0.3"/>
                <circle cx="12" cy="12" r="11" stroke="url(#leaveGrad)" stroke-width="1.5" opacity="0.4"/>
                
                <!-- Círculo con borde punteado (salida) -->
                <circle cx="12" cy="12" r="8" stroke="url(#leaveGrad)" stroke-width="1.5" stroke-dasharray="3,3" fill="none" opacity="0.6"/>
                
                <!-- Icono de salida (puerta con flecha) -->
                <rect x="3" y="4" width="12" height="16" rx="1" stroke="url(#leaveGrad)" stroke-width="1.5" fill="none"/>
                <line x1="3" y1="4" x2="3" y2="20" stroke="url(#leaveGrad)" stroke-width="1.5" opacity="0.4"/>
                <path d="M16 9L20 12L16 15" stroke="url(#leaveGrad)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                <line x1="20" y1="12" x2="11" y2="12" stroke="url(#leaveGrad)" stroke-width="1.8" stroke-linecap="round"/>
                
                <!-- Huellas -->
                <circle cx="6" cy="8" r="1" fill="#E95420" opacity="0.3"/>
                <circle cx="6" cy="12" r="1" fill="#E95420" opacity="0.2"/>
                <circle cx="6" cy="16" r="1" fill="#E95420" opacity="0.1"/>
                
                <!-- Círculo de alerta -->
                <circle cx="17" cy="17" r="2" fill="#2C2C2C" stroke="#E95420" stroke-width="1"/>
                <text x="17" y="18.5" font-size="5" text-anchor="middle" fill="#E95420" font-weight="bold" font-family="'Ubuntu Mono', 'Courier New', monospace;">!</text>
            </svg>
        `;
    }
    
    // 🔥 SI ES INVITACIÓN
    if (extraData && extraData.type === 'workspace_invite') {
        return `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 28px; height: 28px; display: block; flex-shrink: 0;">
                <defs>
                    <linearGradient id="inviteGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#E95420"/>
                        <stop offset="100%" style="stop-color:#77216F"/>
                    </linearGradient>
                    <linearGradient id="inviteGradDark" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#FF6B35"/>
                        <stop offset="100%" style="stop-color:#9945B5"/>
                    </linearGradient>
                </defs>
                
                <circle cx="12" cy="12" r="11" fill="url(#inviteGrad)" opacity="0.15"/>
                <circle cx="12" cy="12" r="11" stroke="url(#inviteGrad)" stroke-width="1.5" opacity="0.3"/>
                <circle cx="12" cy="12" r="10" stroke="url(#inviteGrad)" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.6"/>
                <rect x="4" y="6" width="16" height="12" rx="2" stroke="url(#inviteGrad)" stroke-width="1.8" fill="none"/>
                <polyline points="4,6 12,13 20,6" stroke="url(#inviteGrad)" stroke-width="1.8" stroke-linejoin="round" fill="none"/>
                <rect x="7" y="9" width="10" height="1.5" rx="0.5" fill="url(#inviteGrad)" opacity="0.4"/>
                <rect x="7" y="11.5" width="8" height="1.5" rx="0.5" fill="url(#inviteGrad)" opacity="0.25"/>
                <circle cx="18" cy="18" r="4.5" fill="#111111" stroke="url(#inviteGrad)" stroke-width="1.5"/>
                <line x1="18" y1="15.5" x2="18" y2="20.5" stroke="url(#inviteGrad)" stroke-width="1.5" stroke-linecap="round"/>
                <line x1="15.5" y1="18" x2="20.5" y2="18" stroke="url(#inviteGrad)" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="7" cy="7" r="1" fill="url(#inviteGradDark)" opacity="0.5"/>
                <circle cx="17" cy="7" r="0.5" fill="url(#inviteGradDark)" opacity="0.3"/>
            </svg>
        `;
    }
    
    // ICONOS POR DEFECTO
    const icons = {
        'info': `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 24px; height: 24px; display: block; flex-shrink: 0;">
                <circle cx="12" cy="12" r="11" fill="#2C2C2C" opacity="0.3"/>
                <circle cx="12" cy="12" r="11" stroke="#E95420" stroke-width="1.5" opacity="0.3"/>
                <path d="M12 8V12M12 16H12.01" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
            </svg>
        `,
        'success': `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 24px; height: 24px; display: block; flex-shrink: 0;">
                <circle cx="12" cy="12" r="11" fill="#2C2C2C" opacity="0.3"/>
                <circle cx="12" cy="12" r="11" stroke="#E95420" stroke-width="1.5" opacity="0.3"/>
                <path d="M8 12L11 15L17 9" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `,
        'warning': `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 24px; height: 24px; display: block; flex-shrink: 0;">
                <circle cx="12" cy="12" r="11" fill="#2C2C2C" opacity="0.3"/>
                <circle cx="12" cy="12" r="11" stroke="#E95420" stroke-width="1.5" opacity="0.3"/>
                <path d="M12 8V12M12 16H12.01" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
                <path d="M12 4L12 14M12 4L8 8M12 4L16 8" stroke="#E95420" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
        `,
        'error': `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 24px; height: 24px; display: block; flex-shrink: 0;">
                <circle cx="12" cy="12" r="11" fill="#2C2C2C" opacity="0.3"/>
                <circle cx="12" cy="12" r="11" stroke="#E95420" stroke-width="1.5" opacity="0.3"/>
                <line x1="8" y1="8" x2="16" y2="16" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
                <line x1="16" y1="8" x2="8" y2="16" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
            </svg>
        `
    };
    return icons[type] || icons['info'];
}

function updateBadge(unreadCount) {
    const badge = document.getElementById('unreadBadge');
    if (badge) {
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'inline' : 'none';
    }
}

function updateMarkAllButton(unreadCount) {
    const markBtn = document.getElementById('markAllReadBtn');
    if (markBtn) {
        markBtn.disabled = unreadCount === 0;
    }
}

// ============================================================
// RENDERIZAR NOTIFICACIONES CON BOTONES - ESTILO UBUNTU
// ============================================================

function renderNotifications(notifications, unreadCount) {
    const list = document.getElementById('notificationsList');
    const loading = document.getElementById('loadingState');
    const empty = document.getElementById('emptyState');

    updateBadge(unreadCount);
    updateMarkAllButton(unreadCount);

    if (notifications.length === 0) {
        if (loading) loading.style.display = 'none';
        if (list) list.style.display = 'none';
        if (empty) empty.style.display = 'flex';
        return;
    }

    list.innerHTML = notifications.map(notification => {
        const isUnread = !notification.is_read;
        
        // 🔥 OBTENER parsed_data DEL SERIALIZER
        const extraData = notification.parsed_data || {};
        
        // ✅ SI EXTRA DATA TIENE TEXTO, USARLO (PARA INVITACIONES Y ABANDONOS)
        let displayMessage = notification.message;
        if (extraData && extraData.text) {
            displayMessage = extraData.text;
        }
        
        // 🔥 DETECTAR SI ES NOTIFICACIÓN DE ABANDONO
        const isLeaveNotification = extraData.type === 'user_left_workspace';
        
        const icon = getNotificationIcon(notification.notification_type, extraData);
        const timeAgo = notification.time_ago || getTimeAgo(notification.created_at);
        
        // ✅ DETECTAR SI ES INVITACIÓN
        const isInvitation = extraData.type === 'workspace_invite' || extraData.membership_id;
        
        // ✅ BOTONES DE INVITACIÓN (solo si no es abandono)
        let actionButtons = '';
        if (isInvitation && !isLeaveNotification && isUnread && extraData.membership_id) {
            actionButtons = `
                <div class="invitation-buttons" id="buttons-${notification.id}" style="display: flex; gap: 10px; margin-top: 12px; justify-content: flex-end;">
                    <button id="accept-${notification.id}" 
                            onclick="event.stopPropagation(); window.acceptInvitation('${extraData.membership_id}', '${notification.id}')" 
                            style="
                                background: #e95420;
                                color: #ffffff;
                                border: 1px solid #e95420;
                                padding: 6px 18px;
                                border-radius: 4px;
                                cursor: pointer;
                                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                font-size: 0.8rem;
                                font-weight: 600;
                                transition: all 0.2s ease;
                                letter-spacing: 0.3px;
                            "
                            onmouseover="this.style.background='#d94a1a'; this.style.borderColor='#d94a1a'; this.style.boxShadow='0 0 20px rgba(233,84,32,0.3)';"
                            onmouseout="this.style.background='#e95420'; this.style.borderColor='#e95420'; this.style.boxShadow='none';">
                        ✔ Aceptar
                    </button>
                    <button id="reject-${notification.id}" 
                            onclick="event.stopPropagation(); window.rejectInvitation('${extraData.membership_id}', '${notification.id}')" 
                            style="
                                background: transparent;
                                color: #aea79f;
                                border: 1px solid #555555;
                                padding: 6px 18px;
                                border-radius: 4px;
                                cursor: pointer;
                                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                font-size: 0.8rem;
                                font-weight: 500;
                                transition: all 0.2s ease;
                                letter-spacing: 0.3px;
                            "
                            onmouseover="this.style.borderColor='#888888'; this.style.color='#dfdbd2'; this.style.background='rgba(255,255,255,0.05)';"
                            onmouseout="this.style.borderColor='#555555'; this.style.color='#aea79f'; this.style.background='transparent';">
                        ✘ Rechazar
                    </button>
                </div>
            `;
        }

        return `
            <div class="notification-item ${isUnread ? 'unread' : 'read'}"
                 data-id="${notification.id}"
                 data-membership-id="${extraData.membership_id || ''}"
                 onclick="window.markAsRead('${notification.id}')">
                
                <div class="notification-icon ${notification.notification_type}">
                    ${icon}
                </div>
                
                <div class="notification-content" style="flex: 1;">
                    <div class="title" style="font-weight: ${isUnread ? '600' : '400'}; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        ${notification.title}
                    </div>
                    <div class="message" style="white-space: pre-line; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        ${displayMessage}
                    </div>
                    <div class="time" style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        ${timeAgo}
                    </div>
                    ${actionButtons}
                </div>
                
                <div class="notification-actions" style="display: flex; gap: 4px; align-items: flex-start;">
                    ${isUnread ? `
                        <button onclick="event.stopPropagation(); window.markAsRead('${notification.id}')" 
                                title="Marcar como leída"
                                style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20 6L9 17l-5-5"/>
                            </svg>
                        </button>
                    ` : ''}
                    <button class="delete" onclick="event.stopPropagation(); window.deleteNotification('${notification.id}')" 
                            title="Eliminar"
                            style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 4px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    if (loading) loading.style.display = 'none';
    if (list) list.style.display = 'flex';
    if (empty) empty.style.display = 'none';
}

function showLoading() {
    const list = document.getElementById('notificationsList');
    const loading = document.getElementById('loadingState');
    const empty = document.getElementById('emptyState');
    
    if (loading) loading.style.display = 'flex';
    if (list) list.style.display = 'none';
    if (empty) empty.style.display = 'none';
}

function showError(errorMessage) {
    const list = document.getElementById('notificationsList');
    const loading = document.getElementById('loadingState');
    const empty = document.getElementById('emptyState');
    
    if (loading) loading.style.display = 'none';
    if (list) list.style.display = 'none';
    if (empty) {
        empty.style.display = 'flex';
        const h3 = empty.querySelector('h3');
        const p = empty.querySelector('p');
        if (h3) h3.textContent = 'Error al cargar notificaciones';
        if (p) p.textContent = errorMessage || 'Intenta recargar la página';
    }
}

// ============================================================
// CARGAR NOTIFICACIONES
// ============================================================

async function loadNotifications() {
    console.log('🔄 loadNotifications ejecutado');
    showLoading();
    try {
        const data = await fetchNotifications();
        console.log('📦 Notificaciones:', data);
        renderNotifications(data.notifications || [], data.unread_count || 0);
    } catch (error) {
        console.error('❌ Error loading notifications:', error);
        showError(error.message);
    }
}

window.loadNotifications = loadNotifications;

// ============================================================
// MARCAR COMO LEÍDA
// ============================================================

window.markAsRead = async function(notificationId) {
    console.log('📌 markAsRead - notificationId:', notificationId);
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/notifications/${notificationId}/read/`, {
            method: 'PATCH',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error al marcar como leída');
        }
        
        if (typeof loadNotifications === 'function') {
            await loadNotifications();
        }
        
    } catch (error) {
        console.error('❌ Error al marcar como leída:', error);
    }
};

window.deleteNotification = async function(notificationId) {
    console.log('🗑️ deleteNotification - notificationId:', notificationId);
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/notifications/${notificationId}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Error al eliminar notificación');
        }
        
        if (typeof loadNotifications === 'function') {
            await loadNotifications();
        }
        
    } catch (error) {
        console.error('❌ Error al eliminar notificación:', error);
    }
};

console.log('✅ Notifications UI cargado');
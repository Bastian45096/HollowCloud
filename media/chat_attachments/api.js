// static/js/chat-logic/api.js

// ============================================================
// CONFIGURACIÓN DE API CON TOKEN
// ============================================================

function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
        console.log('✅ Token incluido en la petición');
    } else {
        console.warn('⚠️ No hay token en localStorage');
    }
    
    return headers;
}

// ============================================================
// FUNCIONES BASE CON TOKEN
// ============================================================

async function apiFetch(url, options = {}) {
    const headers = {
        ...getAuthHeaders(),
        ...options.headers
    };
    
    const response = await fetch(url, {
        ...options,
        headers: headers,
        credentials: 'include'
    });
    
    // Si el token expiró, intentar refrescar
    if (response.status === 401) {
        console.warn('⚠️ Token expirado o inválido');
        const refreshed = await refreshToken();
        if (refreshed) {
            const newHeaders = {
                ...getAuthHeaders(),
                ...options.headers
            };
            return fetch(url, {
                ...options,
                headers: newHeaders,
                credentials: 'include'
            });
        } else {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login/';
            throw new Error('Sesión expirada');
        }
    }
    
    return response;
}

// ============================================================
// REFRESCAR TOKEN
// ============================================================

async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;
    
    try {
        const response = await fetch('/api/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            console.log('✅ Token refrescado');
            return true;
        } else {
            console.warn('❌ No se pudo refrescar el token');
            return false;
        }
    } catch (error) {
        console.error('Error refrescando token:', error);
        return false;
    }
}

// ============================================================
// FUNCIÓN PARA MANEJAR 403 (EXPULSIÓN INSTANTÁNEA)
// ============================================================

let isHandlingForbidden = false;

async function handleForbidden(workspaceId) {
    // Evitar múltiples ejecuciones simultáneas
    if (isHandlingForbidden) return;
    isHandlingForbidden = true;
    
    try {
        console.warn('🚫 Acceso denegado al workspace', workspaceId);
        
        // Verificar membresía
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/members/me/`, {
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            console.warn('⚠️ No se pudo verificar membresía, asumiendo expulsado');
        }
        
        const data = await response.json();
        
        if (!data.is_member) {
            console.log('⚠️ Has sido expulsado del workspace', workspaceId);
            
            // Mostrar notificación
            if (typeof window.showToast === 'function') {
                window.showToast('❌ Has sido expulsado de este workspace', 'error');
            } else {
                console.log('❌ Has sido expulsado de este workspace');
            }
            
            // Recargar workspaces y limpiar vista
            if (typeof window.reloadWorkspaces === 'function') {
                await window.reloadWorkspaces();
            }
            
            // Limpiar estado
            if (typeof setActiveWorkspaceId === 'function') {
                setActiveWorkspaceId(null);
            }
            if (typeof setActiveChannelId === 'function') {
                setActiveChannelId(null);
            }
            
            // Limpiar UI
            const area = document.getElementById('messagesArea');
            if (area) {
                area.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted, #888); text-align: center; padding: 40px 20px;">
                        <div style="font-size: 3rem; margin-bottom: 16px;">🚫</div>
                        <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2);">Has sido expulsado</h3>
                        <p style="font-size: 0.9rem;">Ya no eres miembro de este workspace</p>
                    </div>
                `;
            }
            
            const channelItems = document.getElementById('channelItems');
            if (channelItems) {
                channelItems.innerHTML = '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem;">Selecciona un workspace</div>';
            }
            
            // Actualizar header
            const headerTitle = document.querySelector('.header-title');
            if (headerTitle) {
                headerTitle.textContent = 'Chat';
            }
        }
    } catch (error) {
        console.error('❌ Error en handleForbidden:', error);
    } finally {
        isHandlingForbidden = false;
    }
}

// ============================================================
// FUNCIONES API - CON DETECCIÓN DE 403
// ============================================================

async function fetchWorkspaces() {
    try {
        console.log('🔍 fetchWorkspaces llamado');
        const response = await apiFetch('/api/chat/workspaces/');
        console.log('📡 Response recibida:', response);
        
        if (!response || !response.ok) {
            console.error('❌ Error al obtener workspaces:', response?.status || 'sin respuesta');
            return [];
        }
        
        const data = await response.json();
        console.log('📋 Datos parseados de workspaces:', data);
        
        if (Array.isArray(data)) {
            console.log('✅ Es un array directo con', data.length, 'workspaces');
            return data;
        }
        
        if (data && typeof data === 'object' && Array.isArray(data.workspaces)) {
            console.log('✅ Es un objeto con workspaces[] con', data.workspaces.length, 'workspaces');
            return data.workspaces;
        }
        
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            console.log('✅ Es un objeto con results[] con', data.results.length, 'workspaces');
            return data.results;
        }
        
        if (data && typeof data === 'object' && Array.isArray(data.data)) {
            console.log('✅ Es un objeto con data[] con', data.data.length, 'workspaces');
            return data.data;
        }
        
        console.warn('⚠️ No se pudo extraer un array de la respuesta:', data);
        return [];
        
    } catch (error) {
        console.error('❌ Error en fetchWorkspaces:', error);
        return [];
    }
}

async function fetchChannels(workspaceId) {
    if (!workspaceId) return [];
    
    try {
        const response = await apiFetch(`/api/chat/workspaces/${workspaceId}/channels/`);
        
        //  Detectar 403 (expulsión) y actuar inmediatamente
        if (response.status === 403) {
            console.warn('🚫 403 al obtener canales - posible expulsión');
            await handleForbidden(workspaceId);
            return [];
        }
        
        if (!response || !response.ok) {
            console.error('Error al obtener canales:', response?.status || 'sin respuesta');
            return [];
        }
        
        const data = await response.json();
        console.log('📋 Datos de canales:', data);
        
        if (Array.isArray(data)) {
            return data;
        }
        if (data && typeof data === 'object' && Array.isArray(data.channels)) {
            return data.channels;
        }
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        if (data && typeof data === 'object' && Array.isArray(data.data)) {
            return data.data;
        }
        
        return [];
    } catch (error) {
        console.error('Error en fetchChannels:', error);
        return [];
    }
}

async function fetchMessages(channelId) {
    if (!channelId) return [];
    
    try {
        const response = await apiFetch(`/api/chat/workspaces/${getActiveWorkspaceId()}/channels/${channelId}/messages/`);
        
        if (response.status === 403) {
            console.warn('🚫 403 al obtener mensajes - posible expulsión');
            await handleForbidden(getActiveWorkspaceId());
            return [];
        }
        
        if (!response || !response.ok) {
            console.error('Error al obtener mensajes:', response?.status || 'sin respuesta');
            return [];
        }
        
        const data = await response.json();
        console.log('📋 Datos de mensajes:', data);
        
        if (data && Array.isArray(data.messages)) {
            return data.messages;
        }
        if (Array.isArray(data)) {
            return data;
        }
        
        return [];
    } catch (error) {
        console.error('Error en fetchMessages:', error);
        return [];
    }
}

async function fetchWorkspaceMembers(workspaceId) {
    if (!workspaceId) return { members: [] };
    
    try {
        const response = await apiFetch(`/api/chat/workspaces/${workspaceId}/members/?limit=100`);
        
        if (response.status === 403) {
            console.warn('🚫 403 al obtener miembros - posible expulsión');
            await handleForbidden(workspaceId);
            return { members: [] };
        }
        
        if (!response || !response.ok) {
            console.error('Error al obtener miembros:', response?.status || 'sin respuesta');
            return { members: [] };
        }
        
        const data = await response.json();
        console.log('📋 Datos de miembros:', data);
        
        if (data && Array.isArray(data.members)) {
            return data;
        }
        if (Array.isArray(data)) {
            return { members: data };
        }
        
        return { members: [] };
    } catch (error) {
        console.error('Error en fetchWorkspaceMembers:', error);
        return { members: [] };
    }
}

async function searchWorkspacesApi(query) {
    if (!query || query.length < 2) return { workspaces: [], total: 0 };
    
    try {
        const response = await apiFetch(`/api/chat/workspaces/search/?q=${encodeURIComponent(query)}`);
        
        if (!response || !response.ok) {
            console.error('Error al buscar workspaces:', response?.status || 'sin respuesta');
            return { workspaces: [], total: 0 };
        }
        
        const data = await response.json();
        console.log('📋 Datos de búsqueda:', data);
        
        if (data && Array.isArray(data.workspaces)) {
            return data;
        }
        if (Array.isArray(data)) {
            return { workspaces: data, total: data.length };
        }
        
        return { workspaces: [], total: 0 };
    } catch (error) {
        console.error('Error en searchWorkspacesApi:', error);
        return { workspaces: [], total: 0 };
    }
}

async function joinWorkspaceApi(workspaceId) {
    try {
        const response = await apiFetch(`/api/chat/workspaces/${workspaceId}/join/`, {
            method: 'POST',
            body: JSON.stringify({ workspace_id: workspaceId })
        });
        
        const data = await response.json();
        console.log('✅ Respuesta de join:', data);
        return data;
    } catch (error) {
        console.error('Error en joinWorkspaceApi:', error);
        throw error;
    }
}

// static/js/chat-logic/api.js

async function sendMessageToApi(channelId, content, file = null) {
    if (!channelId) return;
    
    try {
        let response;
        
        if (file) {
            const formData = new FormData();
            
            //  Si no hay contenido, enviar un espacio o un placeholder
            // El backend espera que content no esté vacío
            const finalContent = content && content.trim() ? content.trim() : ' ';
            formData.append('content', finalContent);
            formData.append('file', file);
            
            const token = localStorage.getItem('access_token');
            response = await fetch(`/api/chat/workspaces/${getActiveWorkspaceId()}/channels/${channelId}/messages/`, {
                method: 'POST',
                headers: {
                    'Authorization': token ? 'Bearer ' + token : ''
                    //  NO incluir 'Content-Type' para FormData (se establece automáticamente)
                },
                body: formData,
                credentials: 'include'
            });
        } else {
            // 
            if (!content || !content.trim()) {
                throw new Error('El mensaje no puede estar vacío');
            }
            
            response = await apiFetch(`/api/chat/workspaces/${getActiveWorkspaceId()}/channels/${channelId}/messages/`, {
                method: 'POST',
                body: JSON.stringify({ content: content.trim() })
            });
        }
        
        if (response.status === 403) {
            console.warn('🚫 403 al enviar mensaje - posible expulsión');
            await handleForbidden(getActiveWorkspaceId());
            throw new Error('Has sido expulsado de este workspace');
        }
        
        if (!response || !response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || 'Error al enviar mensaje');
        }
        
        const data = await response.json();
        console.log('✅ Mensaje enviado:', data);
        return data;
    } catch (error) {
        console.error('Error en sendMessageToApi:', error);
        throw error;
    }
}

async function editMessageApi(messageId, content) {
    try {
        const response = await apiFetch(`/api/chat/workspaces/${getActiveWorkspaceId()}/channels/${getActiveChannelId()}/messages/${messageId}/`, {
            method: 'PATCH',
            body: JSON.stringify({ content: content })
        });
        
        if (response.status === 403) {
            console.warn('🚫 403 al editar mensaje - posible expulsión');
            await handleForbidden(getActiveWorkspaceId());
            throw new Error('Has sido expulsado de este workspace');
        }
        
        if (!response || !response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Error al editar mensaje');
        }
        
        const data = await response.json();
        console.log('✅ Mensaje editado:', data);
        return data;
    } catch (error) {
        console.error('Error en editMessageApi:', error);
        throw error;
    }
}

async function deleteMessageApi(messageId) {
    try {
        const response = await apiFetch(`/api/chat/workspaces/${getActiveWorkspaceId()}/channels/${getActiveChannelId()}/messages/${messageId}/`, {
            method: 'DELETE'
        });
        
        if (response.status === 403) {
            console.warn('🚫 403 al eliminar mensaje - posible expulsión');
            await handleForbidden(getActiveWorkspaceId());
            throw new Error('Has sido expulsado de este workspace');
        }
        
        if (!response || !response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Error al eliminar mensaje');
        }
        
        console.log('✅ Mensaje eliminado');
        return response;
    } catch (error) {
        console.error('Error en deleteMessageApi:', error);
        throw error;
    }
}

async function kickMemberApi(userId) {
    try {
        const response = await apiFetch(`/api/chat/workspaces/${getActiveWorkspaceId()}/members/`, {
            method: 'DELETE',
            body: JSON.stringify({ user_id: userId })
        });
        
        if (response.status === 403) {
            console.warn('🚫 403 al expulsar - posible expulsión o sin permisos');
            const data = await response.json();
            throw new Error(data.error || 'No tienes permisos para expulsar');
        }
        
        if (!response || !response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Error al expulsar usuario');
        }
        
        const data = await response.json();
        console.log('✅ Usuario expulsado:', data);
        return response;
    } catch (error) {
        console.error('Error en kickMemberApi:', error);
        throw error;
    }
}

// ============================================================
// FUNCIÓN PARA VERIFICAR MEMBRESÍA
// ============================================================

async function checkMembership(workspaceId) {
    try {
        const response = await apiFetch(`/api/chat/workspaces/${workspaceId}/members/me/`);
        
        if (!response || !response.ok) {
            console.warn('⚠️ Error verificando membresía');
            return false;
        }
        
        const data = await response.json();
        return data.is_member === true;
    } catch (error) {
        console.error('Error en checkMembership:', error);
        return false;
    }
}

// ============================================================
// EXPONER FUNCIONES GLOBALES
// ============================================================

window.apiFetch = apiFetch;
window.fetchWorkspaces = fetchWorkspaces;
window.fetchChannels = fetchChannels;
window.fetchMessages = fetchMessages;
window.fetchWorkspaceMembers = fetchWorkspaceMembers;
window.searchWorkspacesApi = searchWorkspacesApi;
window.joinWorkspaceApi = joinWorkspaceApi;
window.sendMessageToApi = sendMessageToApi;
window.editMessageApi = editMessageApi;
window.deleteMessageApi = deleteMessageApi;
window.kickMemberApi = kickMemberApi;
window.refreshToken = refreshToken;
window.checkMembership = checkMembership;
window.handleForbidden = handleForbidden;

console.log('✅ API con autenticación cargada y detección instantánea de expulsión');
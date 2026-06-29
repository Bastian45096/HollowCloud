// static/js/chat-logic/workspace.js

// ============================================================
// FETCH Y SET USER ROLE - CORREGIDO
// ============================================================

window.fetchAndSetUserRole = async function(workspaceId) {
    console.log('📋 fetchAndSetUserRole llamado para:', workspaceId);
    try {
        const token = localStorage.getItem('access_token');
        
        if (!token) {
            console.warn('⚠️ No hay token en localStorage');
            return null;
        }
        
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/members/me/`, {
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('📋 Membresía obtenida:', data);
            return data;
        } else {
            console.warn('⚠️ No se pudo obtener membresía:', response.status);
            return null;
        }
    } catch (e) {
        console.warn('Error obteniendo membresía:', e);
        return null;
    }
};

// ============================================================
// OBTENER WORKSPACES
// ============================================================

window.fetchWorkspaces = async function() {
    try {
        console.log('🔍 fetchWorkspaces ejecutándose');
        const token = localStorage.getItem('access_token');
        
        if (!token) {
            console.warn('⚠️ No hay token en localStorage');
            return [];
        }
        
        const response = await fetch('/api/chat/workspaces/', {
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            console.error('❌ Error:', response.status);
            return [];
        }
        
        const data = await response.json();
        console.log('📋 Datos parseados:', data);
        
        let workspaces = [];
        if (Array.isArray(data)) {
            workspaces = data;
        } else if (data && typeof data === 'object' && Array.isArray(data.workspaces)) {
            workspaces = data.workspaces;
        } else if (data && typeof data === 'object' && Array.isArray(data.results)) {
            workspaces = data.results;
        } else if (data && typeof data === 'object' && Array.isArray(data.data)) {
            workspaces = data.data;
        } else {
            const values = Object.values(data);
            if (values.some(v => typeof v === 'object' && v !== null)) {
                workspaces = values.filter(v => typeof v === 'object' && v !== null);
            }
        }
        
        console.log('✅ Workspaces extraídos:', workspaces.length);
        return workspaces;
        
    } catch (error) {
        console.error('❌ Error en fetchWorkspaces:', error);
        return [];
    }
};

// ============================================================
// OBTENER WORKSPACE POR ID
// ============================================================

window.getWorkspaceById = function(workspaceId) {
    const workspaces = getWorkspaces() || [];
    return workspaces.find(w => w.id === workspaceId) || null;
};

// ============================================================
// VERIFICAR MEMBRESÍA (para usar en otros lugares)
// ============================================================

window.checkWorkspaceMembership = async function(workspaceId) {
    try {
        const token = localStorage.getItem('access_token');
        
        if (!token) {
            console.warn('⚠️ No hay token en localStorage');
            return false;
        }
        
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/members/me/`, {
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('📋 Verificación de membresía:', data);
            return data.is_member === true;
        } else {
            console.warn('⚠️ Error verificando membresía:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ Error en checkWorkspaceMembership:', error);
        return false;
    }
};

console.log('✅ Workspace cargado');
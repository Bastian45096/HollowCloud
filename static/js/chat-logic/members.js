// ============================================================
// NOTA: Las funciones fetchWorkspaceMembers y renderWorkspaceMembers 
// ya están definidas en api.js y ui.js respectivamente
// Este archivo solo contiene funciones específicas de miembros
// ============================================================

// ============================================================
// FUNCIONES DE ADMIN
// ============================================================

async function promoteToAdmin(workspaceId, userId) {
    try {
        //URL corregida con /api/ al inicio
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/promote-admin/`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al ascender a admin');
        }
        
        return data;
    } catch (error) {
 console.error('Error al ascender:', error);
        throw error;
    }
}

// Exponer función global para usar en HTML
window.promoteToAdmin = async function(workspaceId, userId) {
    if (!confirm('¿Estás seguro de que quieres ascender a este usuario a ADMIN?')) {
        return;
    }

    try {
        const result = await promoteToAdmin(workspaceId, userId);
 alert(result.message || 'Usuario ascendido a ADMIN exitosamente');
        
        // Recargar la lista de miembros
        if (typeof loadMembers === 'function') {
            await loadMembers();
        } else {
            location.reload();
        }
        
        return result;
    } catch (error) {
 alert(error.message || 'Error al ascender a admin');
    }
};

// No hay funciones adicionales necesarias aquí
// fetchWorkspaceMembers está en api.js
// renderWorkspaceMembers está en ui.js


// ============================================================
// FUNCIONES DE ADMIN - REVERTIR ADMIN A MEMBER
// ============================================================

async function revertToMember(workspaceId, userId) {
    try {
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/revert-admin/`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: userId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al revertir a miembro');
        }
        
        return data;
    } catch (error) {
 console.error('Error al revertir:', error);
        throw error;
    }
}

// Exponer función global para usar en HTML
window.revertToMember = async function(workspaceId, userId, username) {
    if (!confirm(`¿Estás seguro de que quieres revertir a ${username} de ADMIN a MEMBER?`)) {
        return;
    }

    try {
        const result = await revertToMember(workspaceId, userId);
 alert(result.message || 'Usuario revertido a MEMBER exitosamente');
        
        // Recargar la lista de miembros
        if (typeof loadWorkspaceMembers === 'function') {
            await loadWorkspaceMembers(workspaceId);
        } else {
            location.reload();
        }
        
        return result;
    } catch (error) {
 alert(error.message || 'Error al revertir a miembro');
    }
};


console.log('Members cargado');
// static/js/chat-logic/invite.js

// ============================================================
// INVITAR MIEMBROS
// ============================================================

// Variable global para almacenar el workspace al invitar
let inviteWorkspaceData = null;

// ============================================================
// ABRIR MODAL DE INVITACIÓN
// ============================================================

window.invitarMiembros = function() {
    console.log('🔵 invitarMiembros EJECUTADO');
    
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('Workspace no encontrado', 'error');
        return;
    }
    
    console.log('🔵 Workspace a invitar:', workspace);
    
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    
    // Verificar que sea owner o admin
    const isOwner = currentUserId === ownerId;
    
    // Si no es owner, verificar si es admin (desde el rol del usuario)
    if (!isOwner) {
        // Obtener el rol del usuario en el workspace
        fetchWorkspaceMembers(workspaceId).then(membersData => {
            const userMember = membersData.members?.find(m => m.user?.id === currentUserId);
            if (!userMember || (userMember.role !== 'owner' && userMember.role !== 'admin')) {
                showToast('Solo el owner o admin pueden invitar miembros', 'error');
                return;
            }
            // Si es admin, abrir modal
            openInviteModal(workspace);
        }).catch(() => {
            showToast('Error al verificar permisos', 'error');
        });
        return;
    }
    
    // Si es owner, abrir modal directamente
    openInviteModal(workspace);
};

// ============================================================
// ABRIR MODAL DE INVITACIÓN
// ============================================================

function openInviteModal(workspace) {
    console.log('🔵 openInviteModal EJECUTADO');
    console.log('🔵 Workspace recibido:', workspace);
    
    inviteWorkspaceData = workspace;
    
    // 🔥 VERIFICAR SI EL USUARIO ES OWNER
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    const isOwner = currentUserId === ownerId;
    const workspaceId = getActiveWorkspaceId();
    
    // 🔥 OBTENER EL ROL DEL USUARIO EN EL WORKSPACE
    let userRole = 'member';
    
    // Intentar obtener el rol del usuario actual desde los miembros
    fetchWorkspaceMembers(workspaceId).then(membersData => {
        const userMember = membersData.members?.find(m => m.user?.id === currentUserId);
        if (userMember) {
            userRole = userMember.role || 'member';
        }
        
        // 🔥 DETERMINAR SI PUEDE INVITAR Y CON QUÉ ROLES
        const canInvite = isOwner || userRole === 'owner' || userRole === 'admin';
        
        if (!canInvite) {
            showToast('No tienes permisos para invitar miembros', 'error');
            return;
        }
        
        // 🔥 CONSTRUIR OPCIONES DE ROL SEGÚN PERMISOS
        let roleOptions = '';
        if (isOwner || userRole === 'owner') {
            // OWNER puede invitar como ADMIN o MEMBER
            roleOptions = `
                <option value="member">Miembro</option>
                <option value="admin">Administrador</option>
            `;
        } else {
            // ADMIN solo puede invitar como MEMBER
            roleOptions = `
                <option value="member">Miembro</option>
            `;
        }
        
        // Crear modal dinámicamente
        const modal = document.createElement('div');
        modal.id = 'inviteMemberModal';
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 99999;
            font-family: 'Ubuntu Mono', 'Courier New', monospace;
        `;
        
        modal.innerHTML = `
            <div style="
                background: #111111;
                border: 1px solid #5e2750;
                border-radius: 6px;
                padding: 30px;
                max-width: 450px;
                width: 100%;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
                text-align: center;
            ">
                <div style="
                    margin: 0 auto 16px;
                    width: 64px;
                    height: 64px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    background: rgba(233, 84, 32, 0.1);
                    border: 2px solid rgba(233, 84, 32, 0.3);
                ">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="32" height="32">
                        <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <circle cx="8.5" cy="7" r="4" stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M20 8v6M17 11h6" stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                
                <h2 style="
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                    font-size: 1.1rem;
                    font-weight: 700;
                    color: #dfdbd2;
                    margin-bottom: 8px;
                    letter-spacing: 0.5px;
                ">Invitar a "${workspace.name}"</h2>
                
                <p style="
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                    font-size: 0.85rem;
                    color: #888888;
                    margin-bottom: 20px;
                    line-height: 1.5;
                ">Ingresa el email del usuario que quieres invitar</p>
                
                <form id="inviteMemberForm" style="text-align: left;">
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-size: 0.8rem; color: #888; margin-bottom: 4px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                            Email del usuario
                        </label>
                        <input type="email" id="inviteEmailInput" 
                               placeholder="usuario@email.com"
                               style="
                                   width: 100%;
                                   padding: 10px 14px;
                                   background: #1e1e1e;
                                   border: 1px solid #333333;
                                   border-radius: 4px;
                                   color: #dfdbd2;
                                   font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                   font-size: 0.95rem;
                                   transition: border-color 0.2s;
                                   box-sizing: border-box;
                               "
                               onfocus="this.style.borderColor='#e95420'"
                               onblur="this.style.borderColor='#333333'">
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 0.8rem; color: #888; margin-bottom: 4px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                            Rol
                        </label>
                        <select id="inviteRoleSelect"
                                style="
                                    width: 100%;
                                    padding: 10px 14px;
                                    background: #1e1e1e;
                                    border: 1px solid #333333;
                                    border-radius: 4px;
                                    color: #dfdbd2;
                                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                    font-size: 0.95rem;
                                    transition: border-color 0.2s;
                                    box-sizing: border-box;
                                    cursor: pointer;
                                "
                                onfocus="this.style.borderColor='#e95420'"
                                onblur="this.style.borderColor='#333333'">
                            ${roleOptions}
                        </select>
                        ${!isOwner && userRole === 'admin' ? `
                            <div style="
                                font-size: 0.7rem;
                                color: #888;
                                margin-top: 4px;
                                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                            ">ℹ️ Como administrador, solo puedes invitar como Miembro</div>
                        ` : ''}
                    </div>
                </form>
                
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button onclick="window.closeInviteModal()" style="
                        font-family: 'Ubuntu Mono', 'Courier New', monospace;
                        padding: 10px 28px;
                        background: transparent;
                        border: 1px solid #555555;
                        border-radius: 4px;
                        color: #aea79f;
                        cursor: pointer;
                        font-size: 0.85rem;
                        font-weight: 500;
                        transition: all 0.2s ease;
                        min-width: 100px;
                    " onmouseover="this.style.background='rgba(255,255,255,0.05)'; this.style.borderColor='#888888'; this.style.color='#dfdbd2';" onmouseout="this.style.background='transparent'; this.style.borderColor='#555555'; this.style.color='#aea79f';">
                        Cancelar
                    </button>
                    <button onclick="window.confirmarInvitacion()" style="
                        font-family: 'Ubuntu Mono', 'Courier New', monospace;
                        padding: 10px 28px;
                        background: #e95420;
                        border: 1px solid #e95420;
                        border-radius: 4px;
                        color: #ffffff;
                        cursor: pointer;
                        font-size: 0.85rem;
                        font-weight: 600;
                        transition: all 0.2s ease;
                        min-width: 100px;
                    " onmouseover="this.style.background='#d94a1a'; this.style.borderColor='#d94a1a'; this.style.boxShadow='0 0 20px rgba(233,84,32,0.3)';" onmouseout="this.style.background='#e95420'; this.style.borderColor='#e95420'; this.style.boxShadow='none';">
                        Invitar
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Enfocar el input
        setTimeout(() => {
            const input = document.getElementById('inviteEmailInput');
            if (input) input.focus();
        }, 100);
        
        // Enviar con Enter
        const form = document.getElementById('inviteMemberForm');
        if (form) {
            form.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    window.confirmarInvitacion();
                }
            });
        }
        
        // Cerrar con Escape
        document.addEventListener('keydown', function closeModal(e) {
            if (e.key === 'Escape') {
                const modal = document.getElementById('inviteMemberModal');
                if (modal) {
                    modal.remove();
                    document.removeEventListener('keydown', closeModal);
                }
            }
        });
        
        // Cerrar al hacer clic fuera
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.remove();
            }
        });
        
    }).catch(() => {
        showToast('Error al verificar permisos', 'error');
    });
}


// ============================================================
// CERRAR MODAL DE INVITACIÓN
// ============================================================

window.closeInviteModal = function() {
    const modal = document.getElementById('inviteMemberModal');
    if (modal) {
        modal.remove();
    }
    inviteWorkspaceData = null;
};

// ============================================================
// CONFIRMAR INVITACIÓN
// ============================================================

window.confirmarInvitacion = async function() {
    console.log('🔵 confirmarInvitacion EJECUTADO');
    console.log('🔵 inviteWorkspaceData ACTUAL:', inviteWorkspaceData);
    
    const emailInput = document.getElementById('inviteEmailInput');
    const roleSelect = document.getElementById('inviteRoleSelect');
    
    const email = emailInput ? emailInput.value.trim() : '';
    const role = roleSelect ? roleSelect.value : 'member';
    
    console.log('🔵 Email:', email, 'Rol:', role);
    
    if (!email) {
        showToast('Por favor ingresa un email', 'warning');
        return;
    }
    
    if (!inviteWorkspaceData) {
        console.error('❌ inviteWorkspaceData es null');
        showToast('Error: workspace no encontrado. Por favor, abre el modal nuevamente.', 'error');
        setTimeout(() => window.location.reload(), 2000);
        return;
    }
    
    console.log('🔵 Workspace:', inviteWorkspaceData);
    
    // Guardar datos ANTES de cerrar el modal
    const workspaceData = { ...inviteWorkspaceData };
    
    // Cerrar modal
    window.closeInviteModal();
    
    showToast('Enviando invitacion...', 'info');
    
    try {
        const token = localStorage.getItem('access_token');
        const workspaceId = workspaceData.id;
        const url = `/api/chat/workspaces/${workspaceId}/invite/`;
        
        console.log('🔵 URL:', url);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ email, role })
        });
        
        console.log('🔵 Response status:', response.status);
        
        const data = await response.json();
        console.log('🔵 Respuesta COMPLETA:', data);
        
        if (!response.ok) {
            const errorMsg = data.error || data.message || 'Error al invitar usuario';
            console.error('❌ Error del servidor:', errorMsg);
            showToast('❌ ' + errorMsg, 'error');
            return;
        }
        
        // ✅ OBTENER userId DE FORMA SEGURA
        const userId = data.member?.user_id || data.member?.user?.id || 'desconocido';
        const userEmail = data.member?.email || email;
        
        console.log('✅ Usuario invitado ID:', userId);
        console.log('✅ Usuario invitado Email:', userEmail);
        
        // ✅ MENSAJE DE ÉXITO
        const roleDisplay = role === 'admin' ? 'Administrador' : 'Miembro';
        const currentUser = getCurrentUser();
        const inviterName = currentUser?.username || currentUser?.email || 'Usuario';
        const workspaceName = workspaceData?.name || 'Workspace';
        
        showToast(`✅ ${inviterName} invitó a ${userEmail} como ${roleDisplay} en "${workspaceName}"`, 'success');
        
        // ✅ RECARGAR MIEMBROS
        try {
            const workspaceId2 = getActiveWorkspaceId();
            if (workspaceId2) {
                console.log('🔄 Recargando miembros...');
                const membersData = await fetchWorkspaceMembers(workspaceId2);
                console.log('📋 Miembros recargados:', membersData);
                
                const workspace = getActiveWorkspace();
                if (typeof window.renderWorkspaceMembers === 'function') {
                    window.renderWorkspaceMembers(membersData, workspace);
                }
            }
        } catch (e) {
            console.warn('⚠️ Error al recargar miembros:', e);
        }
        
    } catch (error) {
        console.error('❌ Error al invitar:', error);
        showToast('❌ Error: ' + error.message, 'error');
    }
};

// ============================================================
// ACTUALIZAR VISIBILIDAD DEL BOTÓN INVITAR
// ============================================================

window.updateInviteButtonVisibility = function(workspaceId) {
    const inviteBtn = document.getElementById('inviteMembersBtn');
    if (!inviteBtn) return;
    
    if (!workspaceId) {
        inviteBtn.style.display = 'none';
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        inviteBtn.style.display = 'none';
        return;
    }
    
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    
    if (currentUserId === ownerId) {
        inviteBtn.style.display = 'inline-flex';
    } else {
        fetchWorkspaceMembers(workspaceId).then(membersData => {
            const userMember = membersData.members?.find(m => m.user?.id === currentUserId);
            if (userMember && (userMember.role === 'owner' || userMember.role === 'admin')) {
                inviteBtn.style.display = 'inline-flex';
            } else {
                inviteBtn.style.display = 'none';
            }
        }).catch(() => {
            inviteBtn.style.display = 'none';
        });
    }
};

// ============================================================
// ACEPTAR / RECHAZAR INVITACIONES - CON MODAL DE CARGA
// ============================================================

window.acceptInvitation = async function(membershipId, notificationId) {
    console.log('✅ acceptInvitation - membershipId:', membershipId);
    
    // 🔥 AGREGAR ESTILO DE SPIN SI NO EXISTE
    if (!document.getElementById('spinStyle')) {
        const style = document.createElement('style');
        style.id = 'spinStyle';
        style.textContent = `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`;
        document.head.appendChild(style);
    }
    
    // 🔥 MOSTRAR MODAL DE CARGA
    const modalHtml = `
        <div id="loadingModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999999;
            font-family: 'Ubuntu Mono', 'Courier New', monospace;
        ">
            <div style="
                background: #111111;
                border: 1px solid #e95420;
                border-radius: 8px;
                padding: 40px;
                max-width: 400px;
                width: 100%;
                text-align: center;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
            ">
                <div style="
                    margin: 0 auto 20px;
                    width: 60px;
                    height: 60px;
                    border: 3px solid #e95420;
                    border-top: 3px solid transparent;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                "></div>
                <h3 style="
                    color: #dfdbd2;
                    font-size: 1.1rem;
                    font-weight: 600;
                    margin-bottom: 8px;
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                ">Aceptando Solicitud...</h3>
                <p style="
                    color: #888888;
                    font-size: 0.85rem;
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                ">Por favor espera...</p>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/chat/invitations/${membershipId}/accept/`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        const data = await response.json();
        console.log('📦 Respuesta de aceptar:', data);
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al aceptar invitación');
        }
        
        // 🔥 RECARGAR PÁGINA
        window.location.reload();
        
    } catch (error) {
        console.error('❌ Error al aceptar invitación:', error);
        const modal = document.getElementById('loadingModal');
        if (modal) modal.remove();
        showToast(`❌ ${error.message}`, 'error');
    }
};

window.rejectInvitation = async function(membershipId, notificationId) {
    console.log('❌ rejectInvitation - membershipId:', membershipId);
    
    if (!confirm('¿Estás seguro de que quieres rechazar esta invitación?')) {
        return;
    }
    
    // 🔥 AGREGAR ESTILO DE SPIN SI NO EXISTE
    if (!document.getElementById('spinStyle')) {
        const style = document.createElement('style');
        style.id = 'spinStyle';
        style.textContent = `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`;
        document.head.appendChild(style);
    }
    
    // 🔥 MOSTRAR MODAL DE CARGA
    const modalHtml = `
        <div id="loadingModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999999;
            font-family: 'Ubuntu Mono', 'Courier New', monospace;
        ">
            <div style="
                background: #111111;
                border: 1px solid #e95420;
                border-radius: 8px;
                padding: 40px;
                max-width: 400px;
                width: 100%;
                text-align: center;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
            ">
                <div style="
                    margin: 0 auto 20px;
                    width: 60px;
                    height: 60px;
                    border: 3px solid #e95420;
                    border-top: 3px solid transparent;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                "></div>
                <h3 style="
                    color: #dfdbd2;
                    font-size: 1.1rem;
                    font-weight: 600;
                    margin-bottom: 8px;
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                ">Rechazando Solicitud...</h3>
                <p style="
                    color: #888888;
                    font-size: 0.85rem;
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                ">Por favor espera...</p>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/chat/invitations/${membershipId}/reject/`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        const data = await response.json();
        console.log('📦 Respuesta de rechazar:', data);
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al rechazar invitación');
        }
        
        // 🔥 RECARGAR PÁGINA
        window.location.reload();
        
    } catch (error) {
        console.error('❌ Error al rechazar invitación:', error);
        const modal = document.getElementById('loadingModal');
        if (modal) modal.remove();
        showToast(`❌ ${error.message}`, 'error');
    }
};

console.log('✅ Invite cargado');
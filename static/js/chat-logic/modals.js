// static/js/chat-logic/modals.js

// ============================================================
// MODAL DE BÚSQUEDA
// ============================================================

window.showSearchModal = function() {
    const modal = document.getElementById('searchModal');
    if (modal) {
        modal.style.display = 'flex';
        const input = document.getElementById('searchWorkspaceInput');
        if (input) {
            input.value = '';
            input.focus();
            
            input.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
        }
        const results = document.getElementById('searchResults');
        if (results) {
            results.innerHTML = '<span class="empty-state" style="font-family: \'Ubuntu Mono\', \'Courier New\', monospace;">Ingresa un nombre para buscar workspaces</span>';
        }
    }
};

window.openSearchModal = window.showSearchModal;

window.closeSearchModal = function() {
    const modal = document.getElementById('searchModal');
    if (modal) {
        modal.style.display = 'none';
    }
};

// ============================================================
// MODAL DE EDICIÓN - CON ICONO SVG PERSONALIZADO
// ============================================================

window.openEditModal = function(messageId, content) {
    setEditingMessageId(messageId);
    setEditingMessageContent(content);
    
    const modal = document.getElementById('editModal');
    const textarea = document.getElementById('editMessageInput');
    
    if (!modal) {
        console.warn('⚠️ editModal no encontrado');
        return;
    }
    
  
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-box modal-edit-box" style="
            max-width: 450px;
            text-align: center;
            background: #111111;
            border: 1px solid #5e2750;
            border-radius: 6px;
            padding: 30px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
            position: relative;
            width: 100%;
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
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" 
                          stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" 
                          stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            
            <h2 style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 1.1rem;
                font-weight: 700;
                color: #dfdbd2;
                margin-bottom: 8px;
                letter-spacing: 0.5px;
            ">Editar mensaje</h2>
            
            <p style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 0.85rem;
                color: #888888;
                margin-bottom: 20px;
                line-height: 1.5;
            ">Modifica el contenido de tu mensaje</p>
            
            <div class="edit-input-group" style="margin-bottom: 20px; text-align: left;">
                <textarea id="editMessageInput" rows="3" placeholder="Escribe tu mensaje..." style="
                    width: 100%;
                    padding: 10px 14px;
                    background: #1e1e1e;
                    border: 1px solid #333333;
                    border-radius: 4px;
                    color: #dfdbd2;
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                    font-size: 0.95rem;
                    resize: vertical;
                    transition: border-color 0.2s;
                    box-sizing: border-box;
                " onfocus="this.style.borderColor='#e95420'" onblur="this.style.borderColor='#333333'">${content || ''}</textarea>
            </div>
            
            <div class="edit-actions" style="display: flex; gap: 12px; justify-content: center;">
                <button class="btn-cancel" onclick="window.closeEditModal()" style="
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
                <button class="btn-save" onclick="window.confirmEditMessage()" style="
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
                    Guardar cambios
                </button>
            </div>
        </div>
    `;
    
   
    setTimeout(() => {
        const textarea = document.getElementById('editMessageInput');
        if (textarea) {
            textarea.focus();
            textarea.selectionStart = textarea.value.length;
        }
    }, 100);
    
    
    const textareaEl = document.getElementById('editMessageInput');
    if (textareaEl) {
        textareaEl.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                window.confirmEditMessage();
            }
        });
    }
};

window.closeEditModal = function() {
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.style.display = 'none';
    }
    setEditingMessageId(null);
    setEditingMessageContent(null);
};

// ============================================================
// MODAL DE ELIMINACIÓN - CON ICONO SVG PERSONALIZADO
// ============================================================

window.openDeleteModal = function(messageId) {
    setDeletingMessageId(messageId);
    const modal = document.getElementById('deleteModal');
    
    if (!modal) {
        console.warn('⚠️ deleteModal no encontrado');
        return;
    }
    
    
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-box modal-delete-box" style="
            max-width: 420px;
            text-align: center;
            background: #111111;
            border: 1px solid #5e2750;
            border-radius: 6px;
            padding: 30px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
            position: relative;
            width: 100%;
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
                    <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6h14z" 
                          stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M10 11v6M14 11v6" stroke="#e95420" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </div>
            
            <h2 style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 1.1rem;
                font-weight: 700;
                color: #dfdbd2;
                margin-bottom: 8px;
                letter-spacing: 0.5px;
            "> ¿Eliminar mensaje?</h2>
            
            <p style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 0.85rem;
                color: #888888;
                margin-bottom: 24px;
                line-height: 1.5;
            ">Esta acción no se puede deshacer.</p>
            
            <div class="delete-actions" style="display: flex; gap: 12px; justify-content: center;">
                <button class="btn-cancel" onclick="window.closeDeleteModal()" style="
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
                <button class="btn-delete" onclick="window.confirmDeleteMessage()" style="
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
                    Eliminar
                </button>
            </div>
        </div>
    `;
};

window.closeDeleteModal = function() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.style.display = 'none';
    }
    setDeletingMessageId(null);
};

// ============================================================
// MODAL DE EXPULSIÓN
// ============================================================

window.openKickModal = function(userId, username) {
    setKickingMemberId(userId);
    setKickingMemberName(username);
    
    const modal = document.getElementById('kickModal');
    const title = document.getElementById('kickTitle');
    const subtitle = document.getElementById('kickSubtitle');
    
    if (modal) {
        modal.style.display = 'flex';
    }
    if (title) {
        title.textContent = `¿Expulsar a ${username}?`;
    }
    if (subtitle) {
        subtitle.textContent = `El usuario ${username} ya no podrá acceder a este workspace`;
    }
};

window.closeKickModal = function() {
    const modal = document.getElementById('kickModal');
    if (modal) {
        modal.style.display = 'none';
    }
    setKickingMemberId(null);
    setKickingMemberName(null);
};

window.showKickProcessingModal = function(username) {
    const modal = document.getElementById('kickProcessingModal');
    const title = document.getElementById('kickProcessingTitle');
    const usernameSpan = document.getElementById('kickProcessingUsername');
    
    if (modal) {
        modal.style.display = 'flex';
    }
    if (title) {
        title.textContent = `Expulsando a`;
    }
    if (usernameSpan) {
        usernameSpan.textContent = username || 'usuario';
    }
};

window.closeKickProcessingModal = function() {
    const modal = document.getElementById('kickProcessingModal');
    if (modal) {
        modal.style.display = 'none';
    }
};

// ============================================================
// MODAL DE ABANDONAR WORKSPACE
// ============================================================

window.abandonarWorkspace = function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    if (currentUserId === ownerId) {
        showToast('⚠️ Eres el owner, no puedes abandonar. Puedes eliminar el workspace.', 'warning');
        return;
    }
    
    const modal = document.getElementById('leaveWorkspaceModal');
    const title = document.getElementById('leaveWorkspaceTitle');
    const subtitle = document.getElementById('leaveWorkspaceSubtitle');
    
    if (modal) {
        modal.style.display = 'flex';
    }
    if (title) {
        title.textContent = `¿Abandonar "${workspace.name}"?`;
    }
    if (subtitle) {
        subtitle.textContent = 'Perderás acceso a todos los canales y mensajes';
    }
};

window.closeLeaveWorkspaceModal = function() {
    const modal = document.getElementById('leaveWorkspaceModal');
    if (modal) {
        modal.style.display = 'none';
    }
};

window.confirmarAbandonarWorkspace = async function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const workspaceName = workspace.name || 'Workspace';
    
    const modal = document.getElementById('leaveWorkspaceModal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    const processingModal = document.getElementById('leaveWorkspaceProcessingModal');
    const processingTitle = document.getElementById('leaveWorkspaceProcessingTitle');
    if (processingModal) {
        processingModal.style.display = 'flex';
    }
    if (processingTitle) {
        processingTitle.textContent = `Abandonando "${workspaceName}"...`;
    }
    
    try {
        const token = localStorage.getItem('access_token');
        const currentUser = getCurrentUser();
        
        if (!currentUser || !currentUser.id) {
            throw new Error('No se pudo identificar al usuario');
        }
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/members/`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ user_id: currentUser.id })
        });
        
        if (processingModal) {
            processingModal.style.display = 'none';
        }
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Error al abandonar workspace');
        }
        
        showToast(`Has abandonado "${workspaceName}"`, 'success');
        
        await window.reloadWorkspaces();
        
        setActiveWorkspaceId(null);
        setActiveChannelId(null);
        
        const area = document.getElementById('messagesArea');
        if (area) {
            area.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted, #888); text-align: center; padding: 40px 20px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                    
                    <div style="
                        width: 72px;
                        height: 72px;
                        margin-bottom: 16px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border-radius: 50%;
                        background: rgba(233, 84, 32, 0.1);
                        border: 2px solid rgba(233, 84, 32, 0.3);
                    ">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="36" height="36">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm1-13h-2v6h2V7zm0 8h-2v2h2v-2z" 
                                  fill="#e95420"/>
                            <path d="M15 9l-3 3-3-3-1 1 3 3-3 3 1 1 3-3 3 3 1-1-3-3 3-3z" 
                                  fill="#e95420" opacity="0.6"/>
                        </svg>
                    </div>
                    <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2); font-family: 'Ubuntu Mono', 'Courier New', monospace;">Has abandonado el workspace</h3>
                    <p style="font-size: 0.9rem; font-family: 'Ubuntu Mono', 'Courier New', monospace;">Selecciona otro workspace o únete a uno nuevo</p>
                </div>
            `;
        }
        
        document.getElementById('channelItems').innerHTML = 
            '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem; font-family: \'Ubuntu Mono\', \'Courier New\', monospace;">Selecciona un workspace</div>';
        
        const leaveBtn = document.getElementById('leaveWorkspaceBtn');
        if (leaveBtn) {
            leaveBtn.style.display = 'none';
        }
        
        const headerTitle = document.getElementById('channelTitle');
        if (headerTitle) {
            headerTitle.textContent = 'Selecciona un canal';
            headerTitle.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
        }
        
        const countEl = document.getElementById('messageCount');
        if (countEl) {
            countEl.textContent = '0 mensajes';
        }
        
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.disabled = true;
            messageInput.placeholder = 'Selecciona un workspace...';
            messageInput.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
        }
        
    } catch (error) {
        const processingModal = document.getElementById('leaveWorkspaceProcessingModal');
        if (processingModal) {
            processingModal.style.display = 'none';
        }
        
        console.error('❌ Error al abandonar workspace:', error);
        showToast(`❌ Error: ${error.message}`, 'error');
    }
};

// ============================================================
// MODAL DE ELIMINAR WORKSPACE (solo owner)
// ============================================================

window.eliminarWorkspace = function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    if (currentUserId !== ownerId) {
        showToast('⚠️ Solo el owner puede eliminar el workspace', 'error');
        return;
    }
    
    const modal = document.getElementById('deleteWorkspaceModal');
    const title = document.getElementById('deleteWorkspaceTitle');
    const subtitle = document.getElementById('deleteWorkspaceSubtitle');
    
    if (modal) {
        modal.style.display = 'flex';
    }
    if (title) {
        title.textContent = `¿Eliminar "${workspace.name}"?`;
    }
    if (subtitle) {
        subtitle.textContent = 'Esta acción eliminará el workspace y todos sus canales y mensajes. No se puede deshacer.';
    }
};

window.closeDeleteWorkspaceModal = function() {
    const modal = document.getElementById('deleteWorkspaceModal');
    if (modal) {
        modal.style.display = 'none';
    }
};

window.confirmarEliminarWorkspace = async function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const workspaceName = workspace.name || 'Workspace';
    
    const modal = document.getElementById('deleteWorkspaceModal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    const processingModal = document.getElementById('deleteWorkspaceProcessingModal');
    const processingTitle = document.getElementById('deleteWorkspaceProcessingTitle');
    if (processingModal) {
        processingModal.style.display = 'flex';
    }
    if (processingTitle) {
        processingTitle.textContent = `Eliminando "${workspaceName}"...`;
    }
    
    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (processingModal) {
            processingModal.style.display = 'none';
        }
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Error al eliminar workspace');
        }
        
        showToast(`Has eliminado "${workspaceName}"`, 'success');
        
        setWorkspaces([]);
        
        const workspaceList = document.getElementById('workspaceList');
        if (workspaceList) {
            workspaceList.innerHTML = `
                <div style="padding: 12px; color: var(--text-muted); font-size: 0.8rem; text-align: center;">
                    <div style="font-size: 2rem; margin-bottom: 8px;">🏠</div>
                    No hay workspaces
                    <br>
                    <button onclick="window.openSearchModal()" style="margin-top: 8px; padding: 4px 12px; background: #e95420; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                        Buscar
                    </button>
                </div>
            `;
        }
        
        document.getElementById('channelItems').innerHTML = 
            '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem;">Selecciona un workspace</div>';
        
        document.getElementById('workspaceMembers').innerHTML = '';
        
        const leaveBtn = document.getElementById('leaveWorkspaceBtn');
        if (leaveBtn) {
            leaveBtn.style.display = 'none';
        }
        const deleteBtn = document.getElementById('deleteWorkspaceBtn');
        if (deleteBtn) {
            deleteBtn.style.display = 'none';
        }
        
        const headerTitle = document.getElementById('channelTitle');
        if (headerTitle) {
            headerTitle.textContent = 'Selecciona un canal';
        }
        
        const countEl = document.getElementById('messageCount');
        if (countEl) {
            countEl.textContent = '0 mensajes';
        }
        
        const area = document.getElementById('messagesArea');
        if (area) {
            area.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted, #888); text-align: center; padding: 40px 20px;">
                    <div style="font-size: 3rem; margin-bottom: 16px;">🗑️</div>
                    <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2);">Has eliminado el workspace</h3>
                    <p style="font-size: 0.9rem;">Selecciona otro workspace o crea uno nuevo</p>
                </div>
            `;
        }
        
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.disabled = true;
            messageInput.placeholder = 'Selecciona un workspace...';
        }
        
        setActiveWorkspaceId(null);
        setActiveChannelId(null);
        
        try {
            const freshWorkspaces = await window.fetchWorkspaces();
            console.log('📋 Workspaces después de eliminar:', freshWorkspaces);
            
            if (Array.isArray(freshWorkspaces) && freshWorkspaces.length > 0) {
                setWorkspaces(freshWorkspaces);
                if (typeof window.renderWorkspaces === 'function') {
                    window.renderWorkspaces();
                } else {
                    renderWorkspacesFallback(freshWorkspaces);
                }
                await window.selectWorkspace(freshWorkspaces[0].id);
            } else {
                const workspaceList = document.getElementById('workspaceList');
                if (workspaceList) {
                    workspaceList.innerHTML = `
                        <div style="padding: 12px; color: var(--text-muted); font-size: 0.8rem; text-align: center;">
                            <div style="font-size: 2rem; margin-bottom: 8px;">🏠</div>
                            No hay workspaces disponibles
                            <br>
                            <button onclick="window.openSearchModal()" style="margin-top: 8px; padding: 4px 12px; background: #e95420; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                Buscar
                            </button>
                        </div>
                    `;
                }
            }
        } catch (error) {
            console.error('❌ Error recargando workspaces:', error);
            window.location.reload();
        }
        
    } catch (error) {
        const processingModal = document.getElementById('deleteWorkspaceProcessingModal');
        if (processingModal) {
            processingModal.style.display = 'none';
        }
        
        console.error('❌ Error al eliminar workspace:', error);
        showToast(`❌ Error: ${error.message}`, 'error');
    }
};

// ============================================================
// EDITAR WORKSPACE
// ============================================================

window.editarWorkspace = function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    if (currentUserId !== ownerId) {
        showToast('⚠️ Solo el owner puede editar el workspace', 'error');
        return;
    }
    
    const nameInput = document.getElementById('editWorkspaceNameInput');
    const descInput = document.getElementById('editWorkspaceDescInput');
    
    if (nameInput) {
        nameInput.value = workspace.name || '';
    }
    if (descInput) {
        descInput.value = workspace.description || '';
    }
    
    const modal = document.getElementById('editWorkspaceModal');
    const title = document.getElementById('editWorkspaceTitle');
    const subtitle = document.getElementById('editWorkspaceSubtitle');
    
    if (modal) {
        modal.style.display = 'flex';
    }
    if (title) {
        title.textContent = `Editar "${workspace.name}"`;
    }
    if (subtitle) {
        subtitle.textContent = 'Modifica el nombre y descripción del workspace';
    }
};

window.closeEditWorkspaceModal = function() {
    const modal = document.getElementById('editWorkspaceModal');
    if (modal) {
        modal.style.display = 'none';
    }
};

window.confirmarEditarWorkspace = async function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const nameInput = document.getElementById('editWorkspaceNameInput');
    const descInput = document.getElementById('editWorkspaceDescInput');
    
    const name = nameInput ? nameInput.value.trim() : '';
    const description = descInput ? descInput.value.trim() : '';
    
    if (!name) {
        showToast('⚠️ El nombre no puede estar vacío', 'warning');
        return;
    }
    
    window.closeEditWorkspaceModal();
    
    showToast('⏳ Actualizando workspace...', 'info');
    
    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/`, {
            method: 'PATCH',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                name: name,
                description: description
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || 'Error al actualizar workspace');
        }
        
        const data = await response.json();
        console.log(' Workspace actualizado:', data);
        
        showToast(` Workspace actualizado a "${name}"`, 'success');
        
        const currentWorkspaces = getWorkspaces();
        const updatedWorkspaces = currentWorkspaces.map(w => {
            if (w.id === workspaceId) {
                return { ...w, name: name, description: description };
            }
            return w;
        });
        setWorkspaces(updatedWorkspaces);
        
        if (typeof window.renderWorkspaces === 'function') {
            window.renderWorkspaces();
        }
        
        const updatedWorkspace = getActiveWorkspace();
        updateHeader(updatedWorkspace, null);
        
    } catch (error) {
        console.error('❌ Error al actualizar workspace:', error);
        showToast(`❌ Error: ${error.message}`, 'error');
    }
};

// ============================================================
// EDITAR CANALES
// ============================================================

let canalesCache = [];

window.editarCanales = async function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    if (currentUserId !== ownerId) {
        const members = await fetchWorkspaceMembers(workspaceId);
        const userMember = members.members?.find(m => m.user?.id === currentUserId);
        if (!userMember || (userMember.role !== 'owner' && userMember.role !== 'admin')) {
            showToast('⚠️ Solo el owner o admin pueden editar canales', 'error');
            return;
        }
    }
    
    try {
        const channels = await fetchChannels(workspaceId);
        canalesCache = channels;
        
        const select = document.getElementById('editChannelsSelect');
        if (select) {
            select.innerHTML = '<option value="">-- Selecciona un canal --</option>';
            channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = channel.name || 'Sin nombre';
                select.appendChild(option);
            });
        }
        
        document.getElementById('editChannelForm').style.display = 'none';
        document.getElementById('saveChannelBtn').disabled = true;
        
        const modal = document.getElementById('editChannelsModal');
        const title = document.getElementById('editChannelsTitle');
        const subtitle = document.getElementById('editChannelsSubtitle');
        
        if (modal) {
            modal.style.display = 'flex';
        }
        if (title) {
            title.textContent = `Editar Canales de "${workspace.name}"`;
        }
        if (subtitle) {
            subtitle.textContent = 'Selecciona un canal para editar su nombre';
        }
        
    } catch (error) {
        console.error('❌ Error al cargar canales:', error);
        showToast('❌ Error al cargar canales', 'error');
    }
};

window.cargarDatosCanal = function() {
    const select = document.getElementById('editChannelsSelect');
    const selectedId = select.value;
    
    if (!selectedId) {
        document.getElementById('editChannelForm').style.display = 'none';
        document.getElementById('saveChannelBtn').disabled = true;
        return;
    }
    
    const channel = canalesCache.find(c => c.id === selectedId);
    if (channel) {
        document.getElementById('editChannelNameInput').value = channel.name || '';
        document.getElementById('editChannelDescInput').value = channel.description || '';
        document.getElementById('editChannelForm').style.display = 'block';
        document.getElementById('saveChannelBtn').disabled = false;
    }
};

window.closeEditChannelsModal = function() {
    const modal = document.getElementById('editChannelsModal');
    if (modal) {
        modal.style.display = 'none';
    }
    canalesCache = [];
};

window.confirmarEditarCanal = async function() {
    const select = document.getElementById('editChannelsSelect');
    const channelId = select.value;
    
    if (!channelId) {
        showToast('⚠️ Selecciona un canal', 'warning');
        return;
    }
    
    const nameInput = document.getElementById('editChannelNameInput');
    const descInput = document.getElementById('editChannelDescInput');
    
    const name = nameInput ? nameInput.value.trim() : '';
    const description = descInput ? descInput.value.trim() : '';
    
    if (!name) {
        showToast('⚠️ El nombre del canal no puede estar vacío', 'warning');
        return;
    }
    
    window.closeEditChannelsModal();
    
    showToast('⏳ Actualizando canal...', 'info');
    
    try {
        const token = localStorage.getItem('access_token');
        const workspaceId = getActiveWorkspaceId();
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/channels/${channelId}/`, {
            method: 'PATCH',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                name: name,
                description: description
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || 'Error al actualizar canal');
        }
        
        const data = await response.json();
        console.log(' Canal actualizado:', data);
        
        showToast(` Canal actualizado a "${name}"`, 'success');
        
        const channels = await fetchChannels(workspaceId);
        renderChannels(channels);
        
        if (getActiveChannelId() === channelId) {
            const workspace = getActiveWorkspace();
            const channel = channels.find(c => c.id === channelId);
            updateHeader(workspace, channel);
        }
        
    } catch (error) {
        console.error('❌ Error al actualizar canal:', error);
        showToast(`❌ Error: ${error.message}`, 'error');
    }
};

// ============================================================
// CREAR WORKSPACE
// ============================================================

window.crearWorkspace = function() {
    const modal = document.createElement('div');
    modal.id = 'createWorkspaceModal';
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
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
            <div style="margin-bottom: 16px;">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="48" height="48" style="margin: 0 auto; display: block;">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm1-13h-2v6h2V7zm0 8h-2v2h2v-2z" 
                          fill="#e95420"/>
                    <path d="M15 9l-3 3-3-3-1 1 3 3-3 3 1 1 3-3 3 3 1-1-3-3 3-3z" 
                          fill="#e95420" opacity="0.6"/>
                </svg>
            </div>
            <h2 style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 1.1rem;
                font-weight: 700;
                color: #dfdbd2;
                margin-bottom: 8px;
                letter-spacing: 0.5px;
            ">Crear Workspace</h2>
            <p style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 0.85rem;
                color: #888888;
                margin-bottom: 20px;
                line-height: 1.5;
            ">Ingresa el nombre del nuevo workspace</p>
            
            <form id="createWorkspaceForm" style="text-align: left;">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-size: 0.8rem; color: #888; margin-bottom: 4px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        Nombre del workspace
                    </label>
                    <input type="text" id="createWorkspaceNameInput" 
                           placeholder="Mi nuevo workspace"
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
                        Descripción (opcional)
                    </label>
                    <textarea id="createWorkspaceDescInput" rows="2"
                              placeholder="Descripción del workspace..."
                              style="
                                  width: 100%;
                                  padding: 10px 14px;
                                  background: #1e1e1e;
                                  border: 1px solid #333333;
                                  border-radius: 4px;
                                  color: #dfdbd2;
                                  font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                  font-size: 0.95rem;
                                  resize: vertical;
                                  transition: border-color 0.2s;
                                  box-sizing: border-box;
                              "
                              onfocus="this.style.borderColor='#e95420'"
                              onblur="this.style.borderColor='#333333'"></textarea>
                </div>
            </form>
            
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button onclick="window.cerrarCrearWorkspace()" style="
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
                <button onclick="window.confirmarCrearWorkspace()" style="
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
                    Crear
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    setTimeout(() => {
        const input = document.getElementById('createWorkspaceNameInput');
        if (input) input.focus();
    }, 100);
};

window.cerrarCrearWorkspace = function() {
    const modal = document.getElementById('createWorkspaceModal');
    if (modal) {
        modal.remove();
    }
};

window.confirmarCrearWorkspace = async function() {
    const nameInput = document.getElementById('createWorkspaceNameInput');
    const descInput = document.getElementById('createWorkspaceDescInput');
    
    const name = nameInput ? nameInput.value.trim() : '';
    const description = descInput ? descInput.value.trim() : '';
    
    if (!name) {
        showToast('⚠️ El nombre del workspace es requerido', 'warning');
        return;
    }
    
    window.cerrarCrearWorkspace();
    
    showToast('⏳ Creando workspace...', 'info');
    
    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch('/api/chat/workspaces/', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                name: name,
                description: description
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || 'Error al crear workspace');
        }
        
        const data = await response.json();
        console.log(' Workspace creado:', data);
        
        showToast(` Workspace "${name}" creado`, 'success');
        
        await window.reloadWorkspaces();
        
        if (data.id) {
            await window.selectWorkspace(data.id);
        }
        
    } catch (error) {
        console.error('❌ Error al crear workspace:', error);
        showToast(`❌ Error: ${error.message}`, 'error');
    }
};

// ============================================================
// CREAR CANAL
// ============================================================

window.crearCanal = function() {
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ Selecciona un workspace primero', 'warning');
        return;
    }
    
    const workspace = getActiveWorkspace();
    if (!workspace) {
        showToast('⚠️ Workspace no encontrado', 'error');
        return;
    }
    
    const modal = document.createElement('div');
    modal.id = 'createChannelModal';
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
        animation: fadeIn 0.3s ease;
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
            <div style="margin-bottom: 16px;">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="48" height="48" style="margin: 0 auto; display: block;">
                    <path d="M4 6h16M4 12h16M4 18h16" stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M8 6v12M12 6v12M16 6v12" stroke="#e95420" stroke-width="2" stroke-linecap="round"/>
                    <circle cx="8" cy="12" r="2" fill="#e95420" opacity="0.3"/>
                    <circle cx="12" cy="12" r="2" fill="#e95420" opacity="0.3"/>
                    <circle cx="16" cy="12" r="2" fill="#e95420" opacity="0.3"/>
                </svg>
            </div>
            <h2 style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 1.1rem;
                font-weight: 700;
                color: #dfdbd2;
                margin-bottom: 8px;
                letter-spacing: 0.5px;
            ">Crear Canal</h2>
            <p style="
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
                font-size: 0.85rem;
                color: #888888;
                margin-bottom: 20px;
                line-height: 1.5;
            ">Crea un nuevo canal en "${workspace.name}"</p>
            
            <form id="createChannelForm" style="text-align: left;">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; font-size: 0.8rem; color: #888; margin-bottom: 4px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        Nombre del canal
                    </label>
                    <input type="text" id="createChannelNameInput" 
                           placeholder="Ej: general"
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
                        Descripción (opcional)
                    </label>
                    <textarea id="createChannelDescInput" rows="2"
                              placeholder="Descripción del canal..."
                              style="
                                  width: 100%;
                                  padding: 10px 14px;
                                  background: #1e1e1e;
                                  border: 1px solid #333333;
                                  border-radius: 4px;
                                  color: #dfdbd2;
                                  font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                  font-size: 0.95rem;
                                  resize: vertical;
                                  transition: border-color 0.2s;
                                  box-sizing: border-box;
                              "
                              onfocus="this.style.borderColor='#e95420'"
                              onblur="this.style.borderColor='#333333'"></textarea>
                </div>
            </form>
            
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button onclick="window.cerrarCrearCanal()" style="
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
                <button onclick="window.confirmarCrearCanal()" style="
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
                    Crear
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    setTimeout(() => {
        const input = document.getElementById('createChannelNameInput');
        if (input) input.focus();
    }, 100);
    
    const form = document.getElementById('createChannelForm');
    if (form) {
        form.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                window.confirmarCrearCanal();
            }
        });
    }
    
    document.addEventListener('keydown', function closeModal(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('createChannelModal');
            if (modal) {
                modal.remove();
                document.removeEventListener('keydown', closeModal);
            }
        }
    });
    
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.remove();
        }
    });
};

window.cerrarCrearCanal = function() {
    const modal = document.getElementById('createChannelModal');
    if (modal) {
        modal.remove();
    }
};

window.confirmarCrearCanal = async function() {
    const nameInput = document.getElementById('createChannelNameInput');
    const descInput = document.getElementById('createChannelDescInput');
    
    const name = nameInput ? nameInput.value.trim() : '';
    const description = descInput ? descInput.value.trim() : '';
    
    if (!name) {
        showToast('⚠️ El nombre del canal es requerido', 'warning');
        return;
    }
    
    const workspaceId = getActiveWorkspaceId();
    if (!workspaceId) {
        showToast('⚠️ No hay workspace seleccionado', 'warning');
        return;
    }
    
    window.cerrarCrearCanal();
    
    showToast('⏳ Creando canal...', 'info');
    
    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/channels/`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                name: name,
                description: description
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || 'Error al crear canal');
        }
        
        const data = await response.json();
        console.log(' Canal creado:', data);
        
        showToast(` Canal "${name}" creado`, 'success');
        
        const channels = await fetchChannels(workspaceId);
        if (typeof window.renderChannels === 'function') {
            window.renderChannels(channels);
        }
        
        if (data.id && typeof window.selectChannel === 'function') {
            await window.selectChannel(data.id);
        }
        
    } catch (error) {
        console.error('❌ Error al crear canal:', error);
        showToast(`❌ Error: ${error.message}`, 'error');
    }
};

// ============================================================
// CONFIGURAR LISTENERS DE MODALES
// ============================================================

window.setupModalKeyListeners = function() {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            window.closeSearchModal();
            window.closeEditModal();
            window.closeDeleteModal();
            window.closeKickModal();
            window.closeKickProcessingModal();
            window.closeLeaveWorkspaceModal();
            window.closeDeleteWorkspaceModal();
            window.closePromoteModal();

            const leaveProcessing = document.getElementById('leaveWorkspaceProcessingModal');
            if (leaveProcessing) leaveProcessing.style.display = 'none';
            const deleteProcessing = document.getElementById('deleteWorkspaceProcessingModal');
            if (deleteProcessing) deleteProcessing.style.display = 'none';
        }
    });
    
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.display = 'none';
            }
        });
    });
};

console.log('✅ Modals cargado');

// static/js/chat-logic/modals.js

// ============================================================
// ELIMINAR CANALES
// ============================================================

// ============================================================
// ELIMINAR CANALES - SOLUCIÓN DEFINITIVA
// ============================================================


// static/js/chat-logic/modals.js

// ============================================================
// VARIABLES GLOBALES
// ============================================================

let canalesEliminarCache = [];
let canalAEliminar = null;

// ============================================================
// ELIMINAR CANALES - FUNCION PRINCIPAL
// ============================================================

window.eliminarCanales = async function() {
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
    
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    if (currentUserId !== ownerId) {
        const members = await fetchWorkspaceMembers(workspaceId);
        const userMember = members.members?.find(m => m.user?.id === currentUserId);
        if (!userMember || (userMember.role !== 'owner' && userMember.role !== 'admin')) {
            showToast('Solo el owner o admin pueden eliminar canales', 'error');
            return;
        }
    }
    
    try {
        const channels = await fetchChannels(workspaceId);
        canalesEliminarCache = channels;
        
        const select = document.getElementById('deleteChannelsSelect');
        if (select) {
            select.innerHTML = '<option value="">-- Selecciona un canal --</option>';
            channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                let channelName = channel.name || 'Sin nombre';
                channelName = channelName.replace(/^#+\s*/, '');
                option.textContent = channelName;
                select.appendChild(option);
            });
            
            select.onchange = function() {
                const selectedId = this.value;
                const infoDiv = document.getElementById('deleteChannelInfo');
                const nameSpan = document.getElementById('deleteChannelName');
                const deleteBtn = document.getElementById('deleteChannelBtn');
                
                if (!selectedId) {
                    if (infoDiv) infoDiv.style.display = 'none';
                    if (deleteBtn) {
                        deleteBtn.disabled = true;
                        deleteBtn.style.opacity = '0.5';
                    }
                    return;
                }
                
                const channel = canalesEliminarCache.find(c => c.id === selectedId);
                if (channel) {
                    let channelName = channel.name || 'Sin nombre';
                    channelName = channelName.replace(/^#+\s*/, '');
                    if (nameSpan) nameSpan.textContent = channelName;
                    if (infoDiv) infoDiv.style.display = 'block';
                    if (deleteBtn) {
                        deleteBtn.disabled = false;
                        deleteBtn.style.opacity = '1';
                        deleteBtn.style.cursor = 'pointer';
                    }
                }
            };
        }
        
        if (channels.length > 0 && select) {
            select.value = channels[0].id;
            select.onchange();
        }
        
        const modal = document.getElementById('deleteChannelsModal');
        if (modal) {
            modal.style.display = 'flex';
        }
        
    } catch (error) {
        console.error('Error al cargar canales:', error);
        showToast('Error al cargar canales', 'error');
    }
};

// ============================================================
// CERRAR MODAL DE ELIMINAR CANALES
// ============================================================

window.closeDeleteChannelsModal = function() {
    const modal = document.getElementById('deleteChannelsModal');
    if (modal) {
        modal.style.display = 'none';
    }
    canalesEliminarCache = [];
};

// ============================================================
// CONFIRMAR ELIMINAR CANAL - ABRE MODAL DE CONFIRMACION
// ============================================================

window.confirmarEliminarCanal = function() {
    const select = document.getElementById('deleteChannelsSelect');
    const channelId = select?.value;
    
    if (!channelId) {
        showToast('Selecciona un canal', 'warning');
        return;
    }
    
    const channel = canalesEliminarCache.find(c => c.id === channelId);
    if (!channel) {
        showToast('Canal no encontrado', 'error');
        return;
    }
    
    let channelName = channel.name || 'Canal';
    channelName = channelName.replace(/^#+\s*/, '');
    
    window.openConfirmDeleteChannelModal(channelId, channelName);
};

// ============================================================
// ABRIR MODAL DE CONFIRMACION
// ============================================================

window.openConfirmDeleteChannelModal = function(channelId, channelName) {
    canalAEliminar = {
        id: channelId,
        name: channelName
    };
    
    const modal = document.getElementById('confirmDeleteChannelModal');
    const title = document.getElementById('confirmDeleteChannelTitle');
    const subtitle = document.getElementById('confirmDeleteChannelSubtitle');
    
    if (modal) {
        modal.style.display = 'flex';
    }
    if (title) {
        title.textContent = 'Eliminar canal "' + channelName + '"?';
    }
    if (subtitle) {
        subtitle.textContent = 'Esta accion no se puede deshacer.';
    }
};

// ============================================================
// CERRAR MODAL DE CONFIRMACION
// ============================================================

window.closeConfirmDeleteChannelModal = function() {
    const modal = document.getElementById('confirmDeleteChannelModal');
    if (modal) {
        modal.style.display = 'none';
    }
    canalAEliminar = null;
};

// ============================================================
// CONFIRMAR ELIMINAR CANAL DEFINITIVO
// ============================================================

window.confirmarEliminarCanalDefinitivo = async function() {
    if (!canalAEliminar) {
        showToast('Error: no hay canal seleccionado', 'error');
        return;
    }
    
    const channelId = canalAEliminar.id;
    const channelName = canalAEliminar.name;
    
    window.closeConfirmDeleteChannelModal();
    window.closeDeleteChannelsModal();
    
    const processingModal = document.getElementById('deleteChannelProcessingModal');
    const processingTitle = document.getElementById('deleteChannelProcessingTitle');
    if (processingModal) {
        processingModal.style.display = 'flex';
    }
    if (processingTitle) {
        processingTitle.textContent = 'Eliminando canal...';
    }
    
    try {
        const token = localStorage.getItem('access_token');
        const workspaceId = getActiveWorkspaceId();
        
        const response = await fetch(`/api/chat/workspaces/${workspaceId}/channels/${channelId}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        if (processingModal) {
            processingModal.style.display = 'none';
        }
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || 'Error al eliminar canal');
        }
        
        showToast('Canal "' + channelName + '" eliminado', 'success');
        
        const channels = await fetchChannels(workspaceId);
        if (typeof window.renderChannels === 'function') {
            window.renderChannels(channels);
        }
        
        if (getActiveChannelId() === channelId) {
            setActiveChannelId(null);
            const area = document.getElementById('messagesArea');
            if (area) {
                area.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted, #888); text-align: center; padding: 40px 20px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        <div style="font-size: 3rem; margin-bottom: 16px;">📭</div>
                        <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2); font-family: 'Ubuntu Mono', 'Courier New', monospace;">Selecciona un canal</h3>
                        <p style="font-size: 0.9rem; font-family: 'Ubuntu Mono', 'Courier New', monospace;">Elige un canal para ver los mensajes</p>
                    </div>
                `;
            }
            const messageInput = document.getElementById('messageInput');
            if (messageInput) {
                messageInput.disabled = true;
                messageInput.placeholder = 'Selecciona un canal...';
            }
            const countEl = document.getElementById('messageCount');
            if (countEl) {
                countEl.textContent = '0 mensajes';
            }
        }
        
    } catch (error) {
        if (processingModal) {
            processingModal.style.display = 'none';
        }
        console.error('Error al eliminar canal:', error);
        showToast('Error: ' + error.message, 'error');
    }
    
    canalAEliminar = null;
};

// ============================================================
// MODAL DE PROMOCIÓN A ADMIN
// ============================================================

// Variables globales para el modal de promoción
let promoteData = {
    workspaceId: null,
    userId: null,
    username: null
};

// Abrir modal de confirmación de promoción
window.openPromoteModal = function(workspaceId, userId, username) {
    // Guardar datos
    promoteData.workspaceId = workspaceId;
    promoteData.userId = userId;
    promoteData.username = username;
    
    // Actualizar mensaje
    const usernameSpan = document.getElementById('promoteUsername');
    if (usernameSpan) {
        usernameSpan.textContent = username;
    }
    
    // Mostrar modal
    const modal = document.getElementById('promoteModal');
    if (modal) {
        modal.style.display = 'flex';
    }
    
    // Habilitar botón de confirmar
    const confirmBtn = document.getElementById('confirmPromoteBtn');
    if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Confirmar';
    }
};

// Cerrar modal de promoción
window.closePromoteModal = function() {
    const modal = document.getElementById('promoteModal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    // Limpiar datos
    promoteData.workspaceId = null;
    promoteData.userId = null;
    promoteData.username = null;
};

// Confirmar promoción a admin
window.confirmPromote = async function() {
    const confirmBtn = document.getElementById('confirmPromoteBtn');
    
    // Deshabilitar botón para evitar doble clic
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Ascendiendo...';
    }
    
    try {
        const response = await fetch(`/api/chat/workspaces/${promoteData.workspaceId}/promote-admin/`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: promoteData.userId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al ascender a admin');
        }
        
        // Cerrar modal
        window.closePromoteModal();
        
        // Mostrar éxito
        showToast('✅ Usuario ascendido a ADMIN exitosamente', 'success');
        
        // Recargar lista de miembros
        const workspaceId = promoteData.workspaceId;
        if (typeof loadWorkspaceMembers === 'function') {
            await loadWorkspaceMembers(workspaceId);
        } else {
            location.reload();
        }
        
    } catch (error) {
        // Restaurar botón
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Confirmar';
        }
        
        showToast('❌ Error: ' + (error.message || 'Error al ascender a admin'), 'error');
        console.error('Error al ascender:', error);
    }
};

// ============================================================
// CERRAR MODALES CON ESC (agregar al setup existente)
// ============================================================

// Nota: Ya existe window.setupModalKeyListeners en tu archivo
// Solo asegúrate de que incluya el cierre del modal de promoción
// Si no, agrega esta línea a la función existente:

// En setupModalKeyListeners, dentro del keydown 'Escape':
// window.closePromoteModal();


// ============================================================
// MODAL DE REVERTIR ADMIN A MEMBER
// ============================================================

let revertData = {
    workspaceId: null,
    userId: null,
    username: null
};

// Abrir modal de confirmación de reversión
window.openRevertModal = function(workspaceId, userId, username) {
    revertData.workspaceId = workspaceId;
    revertData.userId = userId;
    revertData.username = username;
    
    const usernameSpan = document.getElementById('revertUsername');
    if (usernameSpan) {
        usernameSpan.textContent = username;
    }
    
    const modal = document.getElementById('revertModal');
    if (modal) {
        modal.style.display = 'flex';
    }
    
    const confirmBtn = document.getElementById('confirmRevertBtn');
    if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Confirmar';
    }
};

// Cerrar modal de reversión
window.closeRevertModal = function() {
    const modal = document.getElementById('revertModal');
    if (modal) {
        modal.style.display = 'none';
    }
    
    revertData.workspaceId = null;
    revertData.userId = null;
    revertData.username = null;
};

// Confirmar reversión
window.confirmRevert = async function() {
    const confirmBtn = document.getElementById('confirmRevertBtn');
    
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Revirtiendo...';
    }
    
    try {
        const response = await fetch(`/api/chat/workspaces/${revertData.workspaceId}/revert-admin/`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: revertData.userId })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error al revertir a miembro');
        }
        
        window.closeRevertModal();
        
        if (typeof showToast === 'function') {
            showToast('✅ Usuario revertido a MEMBER exitosamente', 'success');
        } else {
            alert('✅ Usuario revertido a MEMBER exitosamente');
        }
        
        const workspaceId = revertData.workspaceId;
        if (typeof loadWorkspaceMembers === 'function') {
            await loadWorkspaceMembers(workspaceId);
        } else if (typeof window.loadWorkspaceMembers === 'function') {
            await window.loadWorkspaceMembers(workspaceId);
        } else {
            location.reload();
        }
        
    } catch (error) {
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Confirmar';
        }
        
        if (typeof showToast === 'function') {
            showToast('❌ Error: ' + (error.message || 'Error al revertir'), 'error');
        } else {
            alert('❌ Error: ' + (error.message || 'Error al revertir'));
        }
        console.error('Error al revertir:', error);
    }
};
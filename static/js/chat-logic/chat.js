// static/js/chat-logic/chat.js

let selectedFile = null;
let reloadInterval = null;
let membershipCheckInterval = null;


// ============================================================
// FUNCIONES DE SELECCIÓN - selectWorkspace COMPLETO
// ============================================================

window.selectWorkspace = async function(workspaceId) {
    setActiveWorkspaceId(workspaceId);
    setActiveChannelId(null);
    
    try {
        await fetchAndSetUserRole(workspaceId);
    } catch (error) {
        console.warn('No se pudo obtener el rol:', error);
    }
    
    const workspace = getActiveWorkspace();
    updateHeader(workspace, null);
    
    if (typeof window.renderWorkspaces === 'function') {
        window.renderWorkspaces();
    } else {
        renderWorkspacesFallback(getWorkspaces());
    }

    let channels = [];
    try {
        channels = await fetchChannels(workspaceId);
        if (typeof window.renderChannels === 'function') {
            window.renderChannels(channels);
        } else {
            renderChannelsFallback(channels);
        }
    } catch (error) {
        console.warn('No se pudieron cargar canales:', error);
        document.getElementById('channelItems').innerHTML = 
            '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem; font-family: \'Ubuntu Mono\', \'Courier New\', monospace;">Error al cargar canales</div>';
        channels = [];
    }
    
    try {
        const members = await fetchWorkspaceMembers(workspaceId);
        if (typeof window.renderWorkspaceMembers === 'function') {
            window.renderWorkspaceMembers(members, workspace);
        } else {
            renderWorkspaceMembersFallback(members, workspace);
        }
    } catch (error) {
        console.warn('No se pudieron cargar miembros:', error);
    }

    const area = document.getElementById('messagesArea');
    if (area) {
        area.innerHTML = `
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                color: var(--text-muted, #888);
                text-align: center;
                padding: 40px 20px;
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
            ">
                <div style="font-size: 3rem; margin-bottom: 16px;">📭</div>
                <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2); font-family: 'Ubuntu Mono', 'Courier New', monospace;">Selecciona un canal</h3>
                <p style="font-size: 0.9rem; font-family: 'Ubuntu Mono', 'Courier New', monospace;">Elige un canal para ver los mensajes</p>
            </div>
        `;
    }
    const countEl = document.getElementById('messageCount');
    if (countEl) countEl.textContent = '0 mensajes';
    
    // MOSTRAR/OCULTAR BOTONES DE ACCIONES
    const leaveBtn = document.getElementById('leaveWorkspaceBtn');
    const editWorkspaceBtn = document.getElementById('editWorkspaceBtn');
    const deleteBtn = document.getElementById('deleteWorkspaceBtn');
    const editChannelsBtn = document.getElementById('editChannelsBtn');
    const deleteChannelsBtn = document.getElementById('deleteChannelsBtn');
    const createChannelBtn = document.getElementById('createChannelBtn');
    
    // Si NO hay workspace seleccionado, OCULTAR TODOS LOS BOTONES
    if (!workspaceId) {
        if (leaveBtn) leaveBtn.style.display = 'none';
        if (editWorkspaceBtn) editWorkspaceBtn.style.display = 'none'; // ✅ CORREGIDO
        if (editChannelsBtn) editChannelsBtn.style.display = 'none';
        if (deleteChannelsBtn) deleteChannelsBtn.style.display = 'none';
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (createChannelBtn) createChannelBtn.style.display = 'none';
        return;
    }
    
    // Si HAY workspace seleccionado, mostrar segun el rol
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    const ownerId = workspace?.owner?.id || workspace?.owner_id;
    
    let userRole = 'member';
    try {
        const membersData = await fetchWorkspaceMembers(workspaceId);
        const userMember = membersData.members?.find(m => m.user?.id === currentUserId);
        if (userMember) {
            userRole = userMember.role || 'member';
        }
    } catch (e) {
        console.warn('No se pudo obtener el rol del usuario:', e);
    }
    
    const isOwner = currentUserId === ownerId;
    const isAdmin = userRole === 'admin'
    const hasChannels = channels && channels.length > 0;
    
    console.log('Usuario actual ID:', currentUserId);
    console.log('Owner ID:', ownerId);
    console.log('Es owner?', isOwner);
    console.log('Es admin?', isAdmin);
    console.log('Rol:', userRole);
    console.log('Tiene canales?', hasChannels, 'Cantidad:', channels?.length || 0);
    
    if (workspaceId && isOwner) {
        // Owner: mostrar Editar Workspace, Eliminar Workspace
        if (editWorkspaceBtn) {
            editWorkspaceBtn.style.display = 'flex';
        }
        if (deleteBtn) {
            deleteBtn.style.display = 'flex';
        }
        if (leaveBtn) {
            leaveBtn.style.display = 'none';
        }
        
        // Editar Canales: solo si hay canales
        if (editChannelsBtn) {
            if (hasChannels) {
                editChannelsBtn.style.display = 'flex';
            } else {
                editChannelsBtn.style.display = 'none';
            }
        }
        
        // Eliminar Canales: solo si hay canales
        if (deleteChannelsBtn) {
            if (hasChannels) {
                deleteChannelsBtn.style.display = 'flex';
            } else {
                deleteChannelsBtn.style.display = 'none';
            }
        }
        
        // Crear Canal: siempre visible para owner
        if (createChannelBtn) {
            createChannelBtn.style.display = 'flex';
        }
    } 
    else if (workspaceId && isAdmin && !isOwner) {
        // Admin: mostrar Editar Canales, Eliminar Canales, Abandonar
        if (editWorkspaceBtn) {
            editWorkspaceBtn.style.display = 'none';
        }
        if (deleteBtn) {
            deleteBtn.style.display = 'none';
        }
        if (leaveBtn) {
            leaveBtn.style.display = 'flex';
        }
        
        // Editar Canales: solo si hay canales
        if (editChannelsBtn) {
            if (hasChannels) {
                editChannelsBtn.style.display = 'flex';
            } else {
                editChannelsBtn.style.display = 'none';
            }
        }
        
        // Eliminar Canales: solo si hay canales
        if (deleteChannelsBtn) {
            if (hasChannels) {
                deleteChannelsBtn.style.display = 'flex';
            } else {
                deleteChannelsBtn.style.display = 'none';
            }
        }
        
        // Crear Canal: siempre visible para admin
        if (createChannelBtn) {
            createChannelBtn.style.display = 'flex';
        }
    }
    else if (workspaceId) {
        // Miembro: solo Abandonar
        if (leaveBtn) {
            leaveBtn.style.display = 'flex';
        }
        if (editWorkspaceBtn) {
            editWorkspaceBtn.style.display = 'none';
        }
        if (editChannelsBtn) {
            editChannelsBtn.style.display = 'none';
        }
        if (deleteChannelsBtn) {
            deleteChannelsBtn.style.display = 'none';
        }
        if (deleteBtn) {
            deleteBtn.style.display = 'none';
        }
        if (createChannelBtn) {
            createChannelBtn.style.display = 'none';
        }
    } 
    else {
        if (leaveBtn) leaveBtn.style.display = 'none';
        if (editWorkspaceBtn) editWorkspaceBtn.style.display = 'none';
        if (editChannelsBtn) editChannelsBtn.style.display = 'none';
        if (deleteChannelsBtn) deleteChannelsBtn.style.display = 'none';
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (createChannelBtn) createChannelBtn.style.display = 'none';
    }
    
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.disabled = true;
        messageInput.placeholder = 'Selecciona un canal para escribir...';
        messageInput.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
    }
};

// ============================================================
// FUNCIONES DE BÚSQUEDA
// ============================================================

window.searchWorkspaces = async function() {
    console.log('🔍 searchWorkspaces ejecutándose');
    
    const input = document.getElementById('searchWorkspaceInput');
    const resultsDiv = document.getElementById('searchResults');
    
    if (!input || !resultsDiv) {
        console.error('❌ Elementos de búsqueda no encontrados');
        return;
    }

    const query = input.value.trim();
    console.log('🔍 Buscando:', query);

    if (!query || query.length < 2) {
        resultsDiv.innerHTML = `<span class="empty-state" style="font-family: 'Ubuntu Mono', 'Courier New', monospace; color: var(--text-muted);">
            Ingresa al menos 2 caracteres para buscar
        </span>`;
        return;
    }

    resultsDiv.innerHTML = `<span style="color: var(--text-muted); font-family: 'Ubuntu Mono', 'Courier New', monospace;">
        🔍 Buscando...
    </span>`;

    try {
        const data = await searchWorkspacesApi(query);
        console.log('📋 Resultados:', data);

        if (data.workspaces && data.workspaces.length > 0) {
            let html = `<p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 12px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                Encontrados ${data.total} workspaces:
            </p>`;

            data.workspaces.forEach(workspace => {
                html += `
                    <div class="result-item" style="font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        <div>
                            <div class="name" style="font-family: 'Ubuntu Mono', 'Courier New', monospace;">${workspace.name}</div>
                            <span class="owner" style="font-family: 'Ubuntu Mono', 'Courier New', monospace;">Creado por: ${workspace.owner?.username || 'Usuario'}</span>
                        </div>
                        <button class="join-btn" onclick="window.joinSearchedWorkspace('${workspace.id}')" style="font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                            Unirse
                        </button>
                    </div>
                `;
            });

            resultsDiv.innerHTML = html;
        } else {
            resultsDiv.innerHTML = `<span class="empty-state" style="font-family: 'Ubuntu Mono', 'Courier New', monospace; color: var(--text-muted);">
                No se encontraron workspaces con ese nombre
            </span>`;
        }
    } catch (error) {
        console.error('❌ Error al buscar:', error);
        resultsDiv.innerHTML = `<span class="error-state" style="font-family: 'Ubuntu Mono', 'Courier New', monospace; color: #ff4444;">
            Error: ${error.message}
        </span>`;
    }
};

window.joinSearchedWorkspace = async function(workspaceId) {
    console.log('🔗 Uniéndose al workspace:', workspaceId);
    
    try {
        const data = await joinWorkspaceApi(workspaceId);
        console.log('📋 Respuesta de unión:', data);
        
        if (data.success || data.id || data.already_member) {
            closeSearchModal();
            
            // ✅ FORZAR RECARGA DE WORKSPACES (SIN FILTRAR)
            const freshWorkspaces = await window.fetchWorkspaces();
            console.log('📋 Workspaces frescos:', freshWorkspaces);
            
            if (Array.isArray(freshWorkspaces)) {
                // ✅ Guardar directamente sin filtrar
                setWorkspaces(freshWorkspaces);
                
                // ✅ Renderizar workspaces
                if (typeof window.renderWorkspaces === 'function') {
                    window.renderWorkspaces();
                } else {
                    renderWorkspacesFallback(freshWorkspaces);
                }
                
                // ✅ Buscar el workspace al que nos unimos
                const joinedWorkspace = freshWorkspaces.find(w => w.id === workspaceId);
                
                if (joinedWorkspace) {
                    console.log('✅ Workspace encontrado, seleccionando:', joinedWorkspace.name);
                    await window.selectWorkspace(workspaceId);
                } else {
                    console.warn('⚠️ No se encontró el workspace en la lista, recargando página...');
                    window.location.reload();
                }
            }
            
            if (data.already_member) {
                showToast('ℹ️ Ya eres miembro de este workspace', 'info');
            } else {
                const workspaceName = data.workspace?.name || 'Workspace';
                showToast(`✅ Te has unido a "${workspaceName}"`, 'success');
            }
            return;
        }
        
        const errorMsg = data.message || data.error || 'Error al unirse';
        showToast('❌ ' + errorMsg, 'error');
        console.error('Error al unirse:', data);
        
    } catch (error) {
        console.error('❌ Error al unirse:', error);
        showToast('❌ Error de conexión: ' + error.message, 'error');
    }
};

// ============================================================
// RECARGAR WORKSPACES - CORREGIDO
// ============================================================

window.reloadWorkspaces = async function() {
    try {
        console.log('🔄 Recargando workspaces...');
        
        const currentWorkspaceId = getActiveWorkspaceId();
        const workspaces = await window.fetchWorkspaces();
        console.log('📋 Workspaces obtenidos en reload:', workspaces);
        
        if (!Array.isArray(workspaces)) {
            console.warn('⚠️ workspaces no es un array en reload');
            return [];
        }
        
        const validWorkspaces = await cleanupInaccessibleWorkspaces();
        
        if (typeof setWorkspaces === 'function') {
            setWorkspaces(validWorkspaces);
        }
        
        if (typeof window.renderWorkspaces === 'function') {
            window.renderWorkspaces();
        } else {
            renderWorkspacesFallback(validWorkspaces);
        }
        
        // ✅ Si NO hay workspaces válidos, ocultar todos los botones
        if (validWorkspaces.length === 0) {
            const leaveBtn = document.getElementById('leaveWorkspaceBtn');
            const editWorkspaceBtn = document.getElementById('editWorkspaceBtn');
            const deleteBtn = document.getElementById('deleteWorkspaceBtn');
            const editChannelsBtn = document.getElementById('editChannelsBtn');
            const createChannelBtn = document.getElementById('createChannelBtn');
            
            if (leaveBtn) leaveBtn.style.display = 'none';
            if (editWorkspaceBtn) editWorkspaceBtn.style.display = 'none';
            if (editChannelsBtn) editChannelsBtn.style.display = 'none';
            if (deleteBtn) deleteBtn.style.display = 'none';
            if (createChannelBtn) createChannelBtn.style.display = 'none';
            
            const workspaceListContainer = document.querySelector('.workspace-list');
            if (workspaceListContainer) {
                workspaceListContainer.innerHTML = `
                    <div style="padding: 12px; color: var(--text-muted); font-size: 0.8rem; text-align: center; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                        <div style="font-size: 2rem; margin-bottom: 8px; display: flex; align-items: center; justify-content: center;">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="32" height="32">
                                <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2v11z" 
                                      stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                <path d="M9 14h6" stroke="#e95420" stroke-width="2" stroke-linecap="round"/>
                            </svg>
                        </div>
                        No hay workspaces disponibles
                        <br>
                        <button onclick="window.openSearchModal()" style="margin-top: 8px; padding: 4px 12px; background: #e95420; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                            Buscar
                        </button>
                    </div>
                `;
            }
            
            // ✅ Limpiar también los canales y miembros
            document.getElementById('channelItems').innerHTML = 
                '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem; font-family: \'Ubuntu Mono\', \'Courier New\', monospace;">Selecciona un workspace</div>';
            document.getElementById('workspaceMembers').innerHTML = '';
            
            // ✅ Limpiar área de mensajes
            const area = document.getElementById('messagesArea');
            if (area) {
                area.innerHTML = `
                    <div style="
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100%;
                        color: var(--text-muted, #888);
                        text-align: center;
                        padding: 40px 20px;
                        font-family: 'Ubuntu Mono', 'Courier New', monospace;
                    ">
                        <div style="font-size: 3rem; margin-bottom: 16px;">📭</div>
                        <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2); font-family: 'Ubuntu Mono', 'Courier New', monospace;">Selecciona un workspace</h3>
                        <p style="font-size: 0.9rem; font-family: 'Ubuntu Mono', 'Courier New', monospace;">Crea o únete a un workspace para empezar</p>
                    </div>
                `;
            }
            
            return validWorkspaces;
        }
        
        // ✅ Si hay workspaces pero ninguno seleccionado, asegurar que los botones estén ocultos
        if (validWorkspaces.length > 0 && !getActiveWorkspaceId()) {
            const leaveBtn = document.getElementById('leaveWorkspaceBtn');
            const editWorkspaceBtn = document.getElementById('editWorkspaceBtn');
            const deleteBtn = document.getElementById('deleteWorkspaceBtn');
            const editChannelsBtn = document.getElementById('editChannelsBtn');
            const createChannelBtn = document.getElementById('createChannelBtn');
            
            if (leaveBtn) leaveBtn.style.display = 'none';
            if (editWorkspaceBtn) editWorkspaceBtn.style.display = 'none';
            if (editChannelsBtn) editChannelsBtn.style.display = 'none';
            if (deleteBtn) deleteBtn.style.display = 'none';
            if (createChannelBtn) createChannelBtn.style.display = 'none';
            
            await window.selectWorkspace(validWorkspaces[0].id);
            return validWorkspaces;
        }
        
        if (currentWorkspaceId && validWorkspaces.find(w => w.id === currentWorkspaceId)) {
            console.log('✅ Workspace activo mantenido:', currentWorkspaceId);
            return validWorkspaces;
        }
        
        if (validWorkspaces.length > 0 && currentWorkspaceId) {
            await window.selectWorkspace(validWorkspaces[0].id);
        }
        
        console.log('✅ Workspaces recargados:', validWorkspaces.length);
        return validWorkspaces;
    } catch (error) {
        console.error('Error recargando workspaces:', error);
        return [];
    }
};

// ============================================================
// CONFIRMAR EDICIÓN
// ============================================================

window.confirmEditMessage = async function() {
    const textarea = document.getElementById('editMessageInput');
    if (!textarea) return;

    const newContent = textarea.value.trim();
    if (!newContent) {
        alert('El mensaje no puede estar vacío');
        return;
    }

    const editingMessageId = getEditingMessageId();
    const editingMessageContent = getEditingMessageContent();

    if (newContent === editingMessageContent) {
        closeEditModal();
        return;
    }

    const saveBtn = document.querySelector('.btn-save');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Guardando...';
    }

    try {
        await editMessageApi(editingMessageId, newContent);
        closeEditModal();
        const messages = await fetchMessages(getActiveChannelId());
        if (typeof window.renderMessages === 'function') {
            window.renderMessages(messages);
        } else {
            renderMessagesFallback(messages);
        }
        const workspace = getActiveWorkspace();
        const channels = await fetchChannels(getActiveWorkspaceId());
        const channel = channels.find(c => c.id === getActiveChannelId());
        updateHeader(workspace, channel);
    } catch (error) {
        alert('❌ Error al editar: ' + error.message);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Guardar cambios';
        }
    }
};

// ============================================================
// CONFIRMAR ELIMINACIÓN
// ============================================================

window.confirmDeleteMessage = async function() {
    const deletingMessageId = getDeletingMessageId();
    if (!deletingMessageId) return;

    const deleteBtn = document.querySelector('.btn-delete');
    if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.textContent = 'Eliminando...';
    }

    try {
        const response = await deleteMessageApi(deletingMessageId);
        if (response.ok) {
            closeDeleteModal();
            const messages = await fetchMessages(getActiveChannelId());
            if (typeof window.renderMessages === 'function') {
                window.renderMessages(messages);
            } else {
                renderMessagesFallback(messages);
            }
            const workspace = getActiveWorkspace();
            const channels = await fetchChannels(getActiveWorkspaceId());
            const channel = channels.find(c => c.id === getActiveChannelId());
            updateHeader(workspace, channel);
        } else {
            const data = await response.json();
            alert('❌ Error al eliminar: ' + (data.message || data.error || 'Error desconocido'));
            closeDeleteModal();
        }
    } catch (error) {
        alert('❌ Error de conexión: ' + error.message);
        closeDeleteModal();
    } finally {
        if (deleteBtn) {
            deleteBtn.disabled = false;
            deleteBtn.textContent = 'Eliminar';
        }
    }
};

// ============================================================
// CONFIRMAR EXPULSIÓN
// ============================================================

window.confirmKickMember = async function() {
    const userId = getKickingMemberId();
    const username = getKickingMemberName();
    
    if (!userId) return;

    closeKickModal();
    showKickProcessingModal(username);

    try {
        const response = await kickMemberApi(userId);

        closeKickProcessingModal();

        if (response.ok) {
            window.location.reload();
        } else {
            const data = await response.json();
            console.error('Error al expulsar:', data);
            alert('❌ Error al expulsar a ' + username);
        }
    } catch (error) {
        closeKickProcessingModal();
        console.error('Error de conexión:', error);
        alert('❌ Error de conexión al expulsar a ' + username);
    }
};

// ============================================================
// ENVIAR MENSAJE
// ============================================================

function setupMessageForm() {
    const form = document.getElementById('sendMessageForm');
    const messageInput = document.getElementById('messageInput');
    const fileInput = document.getElementById('fileInput');
    const fileUploadBtn = document.getElementById('fileUploadBtn');
    const filePreview = document.getElementById('filePreview');
    const previewFileName = document.getElementById('previewFileName');
    const previewFileSize = document.getElementById('previewFileSize');
    const removeFileBtn = document.getElementById('removeFileBtn');

    function validateForm() {
        const hasText = messageInput && messageInput.value.trim().length > 0;
        const hasFile = selectedFile !== null;
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            // ✅ Permitir enviar si hay texto O archivo
            submitBtn.disabled = !(hasText || hasFile);
        }
        
        // ✅ CLIP SIEMPRE HABILITADO
        if (fileUploadBtn) {
            fileUploadBtn.disabled = false;
        }
    }

    if (messageInput) {
        messageInput.addEventListener('input', validateForm);
    }

    // ✅ Botón del clip - abre el selector de archivos
    if (fileUploadBtn) {
        fileUploadBtn.disabled = false; // ✅ Asegurar que esté habilitado
        fileUploadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('🖱️ Clip clickeado, abriendo selector...');
            if (fileInput) {
                fileInput.click();
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                
                if (file.size > 10 * 1024 * 1024) {
                    alert('El archivo es demasiado grande. Máximo 10MB.');
                    this.value = '';
                    selectedFile = null;
                    return;
                }
                
                selectedFile = file;
                if (previewFileName) previewFileName.textContent = file.name;
                if (previewFileSize) previewFileSize.textContent = (file.size / 1024).toFixed(1) + ' KB';
                if (filePreview) filePreview.classList.add('show');
                validateForm();
            }
        });
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', function() {
            selectedFile = null;
            if (fileInput) fileInput.value = '';
            if (filePreview) filePreview.classList.remove('show');
            validateForm();
        });
    }

    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            const content = messageInput ? messageInput.value.trim() : '';
            
            // ✅ Permitir enviar SOLO archivo (sin texto)
            if (!content && !selectedFile) {
                console.warn('⚠️ No hay mensaje ni archivo para enviar');
                return;
            }
            
            if (!getActiveChannelId()) {
                showToast('⚠️ Selecciona un canal primero', 'warning');
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Enviando...';
            }

            try {
                // ✅ Si no hay contenido pero hay archivo, enviar un espacio
                // El backend procesará el archivo aunque el texto sea un espacio
                const finalContent = content || ' ';
                
                await sendMessageToApi(getActiveChannelId(), finalContent, selectedFile);
                
                if (messageInput) messageInput.value = '';
                selectedFile = null;
                if (fileInput) fileInput.value = '';
                if (filePreview) filePreview.classList.remove('show');
                validateForm();

                const messages = await fetchMessages(getActiveChannelId());
                await renderMessages(messages);
                const workspace = getActiveWorkspace();
                const channels = await fetchChannels(getActiveWorkspaceId());
                const channel = channels.find(c => c.id === getActiveChannelId());
                updateHeader(workspace, channel);

            } catch (error) {
                alert('❌ Error al enviar mensaje: ' + error.message);
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Enviar';
                }
            }
        });
    }

    // ✅ Inicializar con el clip habilitado
    validateForm();
}
// ============================================================
// AUTO RELOAD (Mensajes)
// ============================================================

function startAutoReload() {
    if (reloadInterval) clearInterval(reloadInterval);
    reloadInterval = setInterval(async () => {
        if (getActiveChannelId() && getActiveWorkspaceId()) {
            try {
                const messages = await fetchMessages(getActiveChannelId());
                const currentMessages = document.querySelectorAll('.message');
                if (messages.length !== currentMessages.length) {
                    if (typeof window.renderMessages === 'function') {
                        window.renderMessages(messages);
                    } else {
                        renderMessagesFallback(messages);
                    }
                    const workspace = getActiveWorkspace();
                    const channels = await fetchChannels(getActiveWorkspaceId());
                    const channel = channels.find(c => c.id === getActiveChannelId());
                    updateHeader(workspace, channel);
                }
            } catch (e) {
                // Silencioso
            }
        }
    }, 30000);
}

// ============================================================
// VERIFICACIÓN DE MEMBRESÍA EN TIEMPO REAL
// ============================================================

function startMembershipCheck() {
    if (membershipCheckInterval) clearInterval(membershipCheckInterval);
    
    membershipCheckInterval = setInterval(async () => {
        const workspaceId = getActiveWorkspaceId();
        if (!workspaceId) return;
        
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`/api/chat/workspaces/${workspaceId}/members/me/`, {
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });
            
            if (!response.ok) {
                console.warn('⚠️ Error verificando membresía');
                return;
            }
            
            const data = await response.json();
            
            if (!data.is_member) {
                console.log(`⚠️ Has sido expulsado del workspace ${workspaceId}`);
                showToast('❌ Has sido expulsado de este workspace', 'error');
                
                await reloadWorkspaces();
                
                setActiveWorkspaceId(null);
                setActiveChannelId(null);
                
                const area = document.getElementById('messagesArea');
                if (area) {
                    area.innerHTML = `
                        <div class="empty-messages">
                            <h3>🚫 Has sido expulsado</h3>
                            <p>Ya no eres miembro de este workspace</p>
                        </div>
                    `;
                }
                
                document.getElementById('channelItems').innerHTML = 
                    '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem;">Selecciona un workspace</div>';
            }
        } catch (error) {
            console.error('❌ Error verificando membresía:', error);
        }
    }, 15000);
}

// ============================================================
// FUNCIONES DE MEMBRESÍA
// ============================================================

async function checkWorkspaceMembership(workspaceId) {
    return true;
}

async function cleanupInaccessibleWorkspaces() {
    try {
        const workspaces = getWorkspaces();
        if (!workspaces || workspaces.length === 0) return [];
        
        const validWorkspaces = [];
        const token = localStorage.getItem('access_token');
        
        for (const workspace of workspaces) {
            try {
                const response = await fetch(`/api/chat/workspaces/${workspace.id}/members/me/`, {
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    },
                    credentials: 'include'
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.is_member) {
                        validWorkspaces.push(workspace);
                    } else {
                        console.log(`⚠️ Workspace ${workspace.name} removido (ya no eres miembro)`);
                        document.querySelectorAll(`[data-workspace-id="${workspace.id}"]`).forEach(el => el.remove());
                    }
                } else {
                    validWorkspaces.push(workspace);
                }
            } catch (error) {
                validWorkspaces.push(workspace);
            }
        }
        
        return validWorkspaces;
    } catch (error) {
        console.error('❌ Error en cleanupInaccessibleWorkspaces:', error);
        return getWorkspaces() || [];
    }
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(message, type = 'success') {
    const oldToast = document.querySelector('.toast-notification');
    if (oldToast) oldToast.remove();
    
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    
    const colors = {
        success:  '#e95420',
        error: '#ff4444',
        info: '#4a9eff',
        warning: '#ffaa00'
    };
    
    // ✅ SIN ICONOS - solo el mensaje
    toast.innerHTML = `
        <span class="toast-message">${message}</span>
    `;
    
    Object.assign(toast.style, {
        position: 'fixed',
        bottom: '30px',
        right: '30px',
        padding: '14px 24px',
        background: 'var(--panel-sidebar)',
        border: `1px solid ${colors[type] || colors.info}`,
        borderRadius: '8px',
        color: 'var(--text-title)',
        fontSize: '0.9rem',
        fontWeight: '500',
        zIndex: '10000',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
        // ✅ FUENTE UBUNTU MONO
        fontFamily: "'Ubuntu Mono', 'Courier New', monospace",
        animation: 'toastSlideIn 0.3s ease'
    });
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Agregar animaciones CSS para toast
const toastStyles = `
    @keyframes toastSlideIn {
        from { transform: translateX(100px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes toastSlideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100px); opacity: 0; }
    }
`;
if (!document.querySelector('#toast-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'toast-styles';
    styleSheet.textContent = toastStyles;
    document.head.appendChild(styleSheet);
}

// ============================================================
// FUNCIONES FALLBACK - En caso de que ui.js no se cargue
// ============================================================

function renderWorkspacesFallback(workspaces) {
    const container = document.getElementById('workspaceList');
    if (!container) return;
    
    if (!Array.isArray(workspaces) || workspaces.length === 0) {
        container.innerHTML = `
            <div style="
            padding: 12px;
            color: var(--text-muted);
            font-size: 0.8rem;
            text-align: center;
            font-family: 'Ubuntu Mono', 'Courier New', monospace;
        ">
            <div style="
                font-size: 2rem;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="32" height="32">
                    <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2v11z" 
                        stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M9 14h6" stroke="#e95420" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </div>
            No hay workspaces
            <br>
            <button onclick="window.openSearchModal()" style="
                margin-top: 8px;
                padding: 4px 12px;
                background: #e95420;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.8rem;
                font-family: 'Ubuntu Mono', 'Courier New', monospace;
            ">
                Buscar
            </button>
        </div>
        `;
        return;
    }
    
    const activeWorkspaceId = getActiveWorkspaceId();
    
    container.innerHTML = workspaces.map(workspace => {
        const isActive = activeWorkspaceId === workspace.id;
        const initial = workspace.name ? workspace.name.charAt(0).toUpperCase() : 'W';
        const shortName = workspace.name ? workspace.name.substring(0, 12) : 'Sin nombre';
        
        return `
            <div class="workspace-item ${isActive ? 'active' : ''}"
                 data-workspace-id="${workspace.id}"
                 onclick="window.selectWorkspace('${workspace.id}')"
                 style="
                    display: flex;
                    align-items: center;
                    padding: 8px 12px;
                    margin: 2px 8px;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    background: ${isActive ? 'var(--accent, #e95420)' : 'transparent'};
                    color: ${isActive ? '#ffffff' : 'var(--text-title, #dfdbd2)'};
                    gap: 10px;
                    position: relative;
                "
                onmouseover="if(!this.classList.contains('active')){this.style.background='rgba(233,84,32,0.15)';}"
                onmouseout="if(!this.classList.contains('active')){this.style.background='transparent';}">
                
                <div class="workspace-avatar" style="
                    width: 32px;
                    height: 32px;
                    border-radius: 6px;
                    background: ${isActive ? 'rgba(255,255,255,0.2)' : 'var(--accent, #e95420)'};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 600;
                    font-size: 14px;
                    flex-shrink: 0;
                    color: ${isActive ? '#ffffff' : '#ffffff'};
                ">
                    ${initial}
                </div>
                
                <div class="workspace-name" style="
                    font-size: 13px;
                    font-weight: ${isActive ? '600' : '400'};
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    flex: 1;
                ">
                    ${shortName}
                </div>
                
                ${isActive ? `
                    <div style="
                        width: 6px;
                        height: 6px;
                        border-radius: 50%;
                        background: #ffffff;
                        flex-shrink: 0;
                    "></div>
                ` : ''}
            </div>
        `;
    }).join('');
}

// static/js/chat-logic/chat.js

function renderChannelsFallback(channels) {
    const container = document.getElementById('channelItems');
    if (!container) return;
    
    if (!Array.isArray(channels) || channels.length === 0) {
        container.innerHTML = `
            <div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem;">
                No hay canales
            </div>
        `;
        return;
    }
    
    const activeChannelId = getActiveChannelId();
    
    container.innerHTML = channels.map(channel => {
        const isActive = activeChannelId === channel.id;
        let channelName = channel.name || 'Sin nombre';
        channelName = channelName.replace(/^#+\s*/, '');
        const displayName = '# ' + channelName;
        
        return `
            <div class="channel-item ${isActive ? 'active' : ''}"
                 data-channel-id="${channel.id}"
                 onclick="window.selectChannel('${channel.id}')"
                 style="
                    display: flex;
                    align-items: center;
                    padding: 6px 12px;
                    margin: 1px 8px;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    background: ${isActive ? 'rgba(233,84,32,0.15)' : 'transparent'};
                    color: ${isActive ? 'var(--accent, #e95420)' : 'var(--text-title, #dfdbd2)'};
                    font-size: 13px;
                    gap: 8px;
                "
                onmouseover="if(!this.classList.contains('active')){this.style.background='rgba(233,84,32,0.08)';}"
                onmouseout="if(!this.classList.contains('active')){this.style.background='transparent';}">
                <span>${displayName}</span>
                ${isActive ? `
                    <span style="
                        width: 4px;
                        height: 4px;
                        border-radius: 50%;
                        background: var(--accent, #e95420);
                        margin-left: auto;
                    "></span>
                ` : ''}
            </div>
        `;
    }).join('');
}

function renderMessagesFallback(messages) {
    const container = document.getElementById('messagesArea');
    if (!container) return;
    
    if (!Array.isArray(messages) || messages.length === 0) {
        container.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted, #888); text-align: center; padding: 40px 20px;">
                <div style="font-size: 3rem; margin-bottom: 16px;">📭</div>
                <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2);">No hay mensajes</h3>
                <p style="font-size: 0.9rem;">Sé el primero en enviar un mensaje</p>
            </div>
        `;
        return;
    }
    
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    // ✅ Obtener el rol del usuario actual
    const workspaceId = getActiveWorkspaceId();
    let currentUserRole = 'member';
    
    // Intentar obtener el rol desde los miembros
    const membersData = window._workspaceMembersData || null;
    if (membersData && membersData.members) {
        const currentMember = membersData.members.find(m => m.user?.id === currentUserId);
        if (currentMember) {
            currentUserRole = currentMember.role || 'member';
        }
    }
    
    container.innerHTML = messages.map(message => {
        const isOwn = message.author?.id === currentUserId;
        const username = message.author?.username || 'Usuario';
        const timestamp = message.created_at ? new Date(message.created_at).toLocaleString() : '';
        const content = message.content || '';
        const messageId = message.id || '';
        const escapedContent = content.replace(/'/g, "\\'");
        
        // ✅ Rol del autor
        const authorRole = message.author?.role || 'member';
        
        // ✅ Lógica de permisos para eliminar
        let canDelete = false;
        if (isOwn) {
            canDelete = true;
        } else if (currentUserRole === 'owner') {
            canDelete = true;
        } else if (currentUserRole === 'admin') {
            if (authorRole === 'member') {
                canDelete = true;
            }
        }
        
        return `
            <div class="message" data-message-id="${messageId}" style="
                display: flex;
                gap: 12px;
                padding: 12px 16px;
                margin: 4px 16px;
                border-radius: 8px;
                background: ${isOwn ? 'rgba(233,84,32,0.08)' : 'transparent'};
                border-left: ${isOwn ? '3px solid var(--accent, #e95420)' : 'none'};
            ">
                <div style="
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    background: var(--accent, #e95420);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #ffffff;
                    font-weight: 600;
                    font-size: 14px;
                    flex-shrink: 0;
                ">
                    ${username.charAt(0).toUpperCase()}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
                        <span style="font-weight: 600; color: var(--text-title, #dfdbd2); font-size: 0.9rem;">${username}</span>
                        <span style="color: var(--text-muted, #888); font-size: 0.7rem;">${timestamp}</span>
                        
                        ${isOwn ? `
                            <button onclick="window.openEditModal('${messageId}', '${escapedContent}')" 
                                    style="
                                        background: none;
                                        border: none;
                                        color: var(--text-muted, #888);
                                        cursor: pointer;
                                        padding: 2px 6px;
                                        border-radius: 4px;
                                        transition: all 0.2s ease;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                    "
                                    onmouseover="this.style.color='var(--accent, #e95420)'; this.style.background='rgba(233,84,32,0.1)';"
                                    onmouseout="this.style.color='var(--text-muted, #888)'; this.style.background='transparent';"
                                    title="Editar mensaje">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" 
                                          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" 
                                          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </button>
                        ` : ''}
                        
                        ${canDelete ? `
                            <button onclick="window.openDeleteModal('${messageId}')" 
                                    style="
                                        background: none;
                                        border: none;
                                        color: var(--text-muted, #888);
                                        cursor: pointer;
                                        padding: 2px 6px;
                                        border-radius: 4px;
                                        transition: all 0.2s ease;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                    "
                                    onmouseover="this.style.color='#ff4444'; this.style.background='rgba(255,68,68,0.1)';"
                                    onmouseout="this.style.color='var(--text-muted, #888)'; this.style.background='transparent';"
                                    title="Eliminar mensaje">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6h14z" 
                                          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M10 11v6M14 11v6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                                </svg>
                            </button>
                        ` : ''}
                    </div>
                    <div style="color: var(--text-body, #dfdbd2); font-size: 0.95rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word;">${content}</div>
                </div>
            </div>
        `;
    }).join('');
}

function renderWorkspaceMembersFallback(membersData, workspace) {
    const container = document.getElementById('workspaceMembers');
    if (!container) return;
    
    const members = membersData?.members || [];
    const count = members.length;
    
    if (!Array.isArray(members) || members.length === 0) {
        container.innerHTML = `
            <div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem;">
                No hay miembros
            </div>
        `;
        return;
    }
    
    let html = `
        <div style="padding: 8px 12px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted, #888); border-top: 1px solid var(--border-color, #2a2a2a); margin-top: 8px; padding-top: 12px;">
            Miembros (${count})
        </div>
    `;
    
    members.slice(0, 10).forEach(member => {
        const user = member.user || {};
        const username = user.username || 'Usuario';
        const initial = username.charAt(0).toUpperCase();
        const userId = user.id || '';
        
        html += `
            <div class="member-item" data-user-id="${userId}" style="display: flex; align-items: center; padding: 4px 12px; gap: 10px; border-radius: 4px; cursor: default;">
                <div style="width: 28px; height: 28px; border-radius: 50%; background: rgba(233,84,32,0.4); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; color: #ffffff; flex-shrink: 0;">${initial}</div>
                <span style="font-size: 0.85rem; color: var(--text-title, #dfdbd2); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${username}</span>
            </div>
        `;
    });
    
    if (count > 10) {
        html += `
            <div style="padding: 4px 12px; color: var(--text-muted); font-size: 0.7rem; text-align: center;">
                +${count - 10} más
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// ============================================================
// RECARGAR WORKSPACES
// ============================================================

window.reloadWorkspaces = async function() {
    try {
        console.log('🔄 Recargando workspaces...');
        
        const currentWorkspaceId = getActiveWorkspaceId();
        const workspaces = await window.fetchWorkspaces();
        console.log('📋 Workspaces obtenidos en reload:', workspaces);
        
        if (!Array.isArray(workspaces)) {
            console.warn('⚠️ workspaces no es un array en reload');
            return [];
        }
        
        const validWorkspaces = await cleanupInaccessibleWorkspaces();
        
        if (typeof setWorkspaces === 'function') {
            setWorkspaces(validWorkspaces);
        }
        
        if (typeof window.renderWorkspaces === 'function') {
            window.renderWorkspaces();
        } else {
            renderWorkspacesFallback(validWorkspaces);
        }
        
        if (validWorkspaces.length === 0) {
            const workspaceListContainer = document.querySelector('.workspace-list');
            if (workspaceListContainer) {
                workspaceListContainer.innerHTML = `
                    <div style="
                        padding: 12px;
                        color: var(--text-muted);
                        font-size: 0.8rem;
                        text-align: center;
                        font-family: 'Ubuntu Mono', 'Courier New', monospace;
                    ">
                        <div style="
                            font-size: 2rem;
                            margin-bottom: 8px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        ">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="32" height="32">
                                <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2v11z" 
                                    stroke="#e95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                <path d="M9 14h6" stroke="#e95420" stroke-width="2" stroke-linecap="round"/>
                            </svg>
                        </div>
                        No hay workspaces
                        <br>
                        <button onclick="window.openSearchModal()" style="
                            margin-top: 8px;
                            padding: 4px 12px;
                            background: #e95420;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 0.8rem;
                            font-family: 'Ubuntu Mono', 'Courier New', monospace;
                        ">
                            Buscar
                        </button>
                    </div>
                `;
            }
        }
        
        if (validWorkspaces.length > 0 && !getActiveWorkspaceId()) {
            await window.selectWorkspace(validWorkspaces[0].id);
        } else if (currentWorkspaceId && validWorkspaces.find(w => w.id === currentWorkspaceId)) {
            console.log('✅ Workspace activo mantenido:', currentWorkspaceId);
        } else if (validWorkspaces.length > 0 && currentWorkspaceId) {
            await window.selectWorkspace(validWorkspaces[0].id);
        }
        
        console.log('✅ Workspaces recargados:', validWorkspaces.length);
        return validWorkspaces;
    } catch (error) {
        console.error('Error recargando workspaces:', error);
        return [];
    }
};

// ============================================================
// INICIALIZACIÓN
// ============================================================

async function init() {
    const token = getToken();
    if (!token) {
        console.log('⚠️ No hay token, redirigiendo a login...');
        window.location.href = '/login/';
        return;
    }

    console.log('✅ Token encontrado, iniciando chat...');
    
    // Intentar obtener usuario
    try {
        await fetchCurrentUser();
    } catch (e) {
        console.warn('⚠️ No se pudo obtener usuario, continuando...');
    }

    // ✅ Obtener workspaces usando la NUEVA función
    let workspaces = [];
    try {
        workspaces = await window.fetchWorkspaces();
        console.log('📋 Workspaces obtenidos en init:', workspaces);
    } catch (error) {
        console.error('❌ Error al obtener workspaces:', error);
    }
    
    // ✅ Verificar que workspaces sea un array
    if (!Array.isArray(workspaces)) {
        console.warn('⚠️ workspaces no es un array, usando array vacío');
        workspaces = [];
    }
    
    console.log('📋 Workspaces finales:', workspaces.length);
    
    // Guardar en el estado global
    if (typeof setWorkspaces === 'function') {
        setWorkspaces(workspaces);
    }
    
    // ✅ Renderizar workspaces - con fallback
    if (typeof window.renderWorkspaces === 'function') {
        window.renderWorkspaces();
    } else {
        console.warn('⚠️ renderWorkspaces no está definida, usando fallback');
        renderWorkspacesFallback(workspaces);
    }

    if (workspaces.length === 0) {
        document.getElementById('channelItems').innerHTML = 
            '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem;"></div>';
        return;
    }

    // Seleccionar el primer workspace
    await window.selectWorkspace(workspaces[0].id);
    
    // Iniciar verificación de membresía
    startMembershipCheck();
    
    setupModalKeyListeners();
    setupMessageForm();
    startAutoReload();
}


// static/js/chat-logic/chat.js

// ============================================================
// ABANDONAR WORKSPACE
// ============================================================

window.leaveWorkspace = async function() {
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
    
    // ✅ Confirmar con el usuario
    if (!confirm(`¿Estás seguro de que quieres abandonar el workspace "${workspace.name}"?\n\nPerderás acceso a todos los canales y mensajes.`)) {
        return;
    }
    
    try {
        showToast('⏳ Abandonando workspace...', 'info');
        
        const token = localStorage.getItem('access_token');
        const currentUser = getCurrentUser();
        
        if (!currentUser || !currentUser.id) {
            showToast('❌ No se pudo identificar al usuario', 'error');
            return;
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
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Error al abandonar workspace');
        }
        
        showToast(`✅ Has abandonado el workspace "${workspace.name}"`, 'success');
        
        // ✅ Recargar workspaces
        await reloadWorkspaces();
        
        // ✅ Limpiar vista
        setActiveWorkspaceId(null);
        setActiveChannelId(null);
        
        const area = document.getElementById('messagesArea');
        if (area) {
            area.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted, #888); text-align: center; padding: 40px 20px;">
                    <div style="font-size: 3rem; margin-bottom: 16px;">👋</div>
                    <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2);">Has abandonado el workspace</h3>
                    <p style="font-size: 0.9rem;">Selecciona otro workspace o únete a uno nuevo</p>
                </div>
            `;
        }
        
        document.getElementById('channelItems').innerHTML = 
            '<div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem;">Selecciona un workspace</div>';
        
        // ✅ Ocultar el botón de abandonar
        const leaveBtn = document.getElementById('leaveWorkspaceBtn');
        if (leaveBtn) {
            leaveBtn.style.display = 'none';
        }
        
        // ✅ Actualizar header
        const headerTitle = document.getElementById('channelTitle');
        if (headerTitle) {
            headerTitle.textContent = 'Selecciona un canal';
        }
        
        const countEl = document.getElementById('messageCount');
        if (countEl) {
            countEl.textContent = '0 mensajes';
        }
        
    } catch (error) {
        console.error('❌ Error al abandonar workspace:', error);
        showToast(`❌ Error: ${error.message}`, 'error');
    }
};

// ============================================================
// CLEANUP
// ============================================================

window.addEventListener('beforeunload', () => {
    if (reloadInterval) clearInterval(reloadInterval);
    if (membershipCheckInterval) clearInterval(membershipCheckInterval);
});

// ============================================================
// INICIAR
// ============================================================

document.addEventListener('DOMContentLoaded', init);

// ============================================================
// EXPONER FUNCIONES GLOBALES
// ============================================================

window.showToast = showToast;
window.cleanupInaccessibleWorkspaces = cleanupInaccessibleWorkspaces;
window.checkWorkspaceMembership = checkWorkspaceMembership;
window.startMembershipCheck = startMembershipCheck;
window.reloadWorkspaces = reloadWorkspaces;

console.log('✅ Chat inicializado correctamente');
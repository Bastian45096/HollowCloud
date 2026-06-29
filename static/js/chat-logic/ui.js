// static/js/chat-logic/ui.js

// ============================================================
// RENDERIZAR WORKSPACES
// ============================================================

window.renderWorkspaces = function() {
    console.log('📋 renderWorkspaces llamado');
    const container = document.getElementById('workspaceList');
    if (!container) {
        console.warn('⚠️ workspaceList no encontrado');
        return;
    }
    
    const workspaces = getWorkspaces() || [];
    console.log('📋 Renderizando workspaces:', workspaces.length);
    
    if (!Array.isArray(workspaces) || workspaces.length === 0) {
        container.innerHTML = `
            <div style="padding: 12px; color: var(--text-muted); font-size: 0.8rem; text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 8px;">🏠</div>
                No hay workspaces
                <br>
                <button onclick="window.openSearchModal()" style="margin-top: 8px; padding: 4px 12px; background: #e95420; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
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
        
        return `
            <div class="workspace-item ${isActive ? 'active' : ''}"
                 data-workspace-id="${workspace.id}"
                 onclick="window.selectWorkspace('${workspace.id}')"
                 title="${workspace.name || 'Sin nombre'}"
                 style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 4px;
                    margin: 4px auto;
                    width: 40px;
                    height: 40px;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    background: ${isActive ? 'var(--accent, #e95420)' : 'transparent'};
                    border: ${isActive ? '2px solid var(--accent, #e95420)' : '2px solid transparent'};
                    position: relative;
                "
                onmouseover="if(!this.classList.contains('active')){this.style.background='rgba(233,84,32,0.15)'; this.style.borderColor='rgba(233,84,32,0.3)';}"
                onmouseout="if(!this.classList.contains('active')){this.style.background='transparent'; this.style.borderColor='transparent';}">
                
                <div class="workspace-avatar" style="
                    width: 32px;
                    height: 32px;
                    border-radius: 6px;
                    background: ${isActive ? 'rgba(255,255,255,0.2)' : 'var(--accent, #e95420)'};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 600;
                    font-size: 16px;
                    flex-shrink: 0;
                    color: ${isActive ? '#ffffff' : '#ffffff'};
                    transition: all 0.2s ease;
                ">
                    ${initial}
                </div>
                
                ${isActive ? `
                    <div style="
                        position: absolute;
                        right: -4px;
                        top: 50%;
                        transform: translateY(-50%);
                        width: 4px;
                        height: 20px;
                        border-radius: 2px;
                        background: var(--accent, #e95420);
                    "></div>
                ` : ''}
            </div>
        `;
    }).join('');
};

// ============================================================
// RENDERIZAR CANALES 
// ============================================================



window.renderChannels = function(channels) {
    console.log('📋 renderChannels llamado');
    const container = document.getElementById('channelItems');
    if (!container) {
        console.warn('⚠️ channelItems no encontrado');
        return;
    }
    
    if (!Array.isArray(channels) || channels.length === 0) {
        container.innerHTML = `
            <div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                No hay canales
            </div>
        `;
        return;
    }
    
    const activeChannelId = getActiveChannelId();
    
    container.innerHTML = channels.map(channel => {
        const isActive = activeChannelId === channel.id;
        //  Obtener el nombre del canal
        let channelName = channel.name || 'Sin nombre';
        //  Eliminar TODOS los # del inicio
        channelName = channelName.replace(/^#+\s*/, '');
        //  Mostrar SOLO el nombre sin # adicional
        // El # ya está en el nombre original, no lo agregamos de nuevo
        const displayName = channelName;
        
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
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                "
                onmouseover="if(!this.classList.contains('active')){this.style.background='rgba(233,84,32,0.08)';}"
                onmouseout="if(!this.classList.contains('active')){this.style.background='transparent';}">
                <span style="font-family: 'Ubuntu Mono', 'Courier New', monospace;">${displayName}</span>
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
};
// ============================================================
// RENDERIZAR MIEMBROS - CON CRUZ NARANJA
// ============================================================

window.renderWorkspaceMembers = function(membersData, workspace) {
    console.log('📋 renderWorkspaceMembers llamado');
    const container = document.getElementById('workspaceMembers');
    if (!container) {
        console.warn('⚠️ workspaceMembers no encontrado');
        return;
    }
    
    const members = membersData?.members || [];
    const count = members.length;
    
    if (!Array.isArray(members) || members.length === 0) {
        container.innerHTML = `
            <div style="padding: 8px 12px; color: var(--text-muted); font-size: 0.8rem; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                No hay miembros
            </div>
        `;
        return;
    }
    
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    let isAdmin = false;
    for (const member of members) {
        if (member.user?.id === currentUserId) {
            if (member.role === 'owner' || member.role === 'admin') {
                isAdmin = true;
            }
            break;
        }
    }
    
    let html = `
        <div style="
            padding: 8px 12px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted, #888);
            border-top: 1px solid var(--border-color, #2a2a2a);
            margin-top: 8px;
            padding-top: 12px;
            font-family: 'Ubuntu Mono', 'Courier New', monospace;
        ">Miembros (${count})</div>
    `;
    
    members.slice(0, 10).forEach(member => {
        const user = member.user || {};
        const username = user.username || 'Usuario';
        const role = member.role || 'member';
        const isOwner = role === 'owner';
        const isAdminUser = role === 'admin';
        const userId = user.id || '';
        const initial = username.charAt(0).toUpperCase();
        const isCurrentUser = userId === currentUserId;
        
        const showKickButton = !isCurrentUser && isAdmin && !isOwner;
        
        const avatarUrl = user.avatar;
        let avatarHtml = '';
        
        if (avatarUrl) {
            avatarHtml = `
                <img src="${avatarUrl}" 
                     alt="${username}"
                     style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover; flex-shrink: 0; background: var(--accent, #e95420);"
                     onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'width:28px;height:28px;border-radius:50%;background:var(--accent,#e95420);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:12px;flex-shrink:0;font-family:\\'Ubuntu Mono\\', \\'Courier New\\', monospace;\\'>${initial}</div>';"
                >
            `;
        } else {
            avatarHtml = `
                <div style="width: 28px; height: 28px; border-radius: 50%; background: ${isOwner ? 'var(--accent, #e95420)' : 'rgba(233,84,32,0.4)'}; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; color: #ffffff; flex-shrink: 0; font-family: 'Ubuntu Mono', 'Courier New', monospace;">${initial}</div>
            `;
        }
        
        let roleText = '';
        if (isOwner) {
            roleText = 'Owner';
        } else if (isAdminUser) {
            roleText = 'Admin';
        }
        
        const kickButtonHtml = showKickButton ? `
            <button onclick="window.openKickModal('${userId}', '${username}')" 
                    style="background: none; border: none; color: #e95420; cursor: pointer; font-size: 16px; padding: 0 4px; opacity: 0.6; transition: all 0.2s; font-weight: bold; line-height: 1; font-family: 'Ubuntu Mono', 'Courier New', monospace;" 
                    onmouseover="this.style.opacity='1'; this.style.transform='scale(1.2)';" 
                    onmouseout="this.style.opacity='0.6'; this.style.transform='scale(1)';"
                    title="Expulsar a ${username}">
                ✕
            </button>
        ` : '';
        
        html += `
            <div class="member-item" data-user-id="${userId}" style="display: flex; align-items: center; padding: 4px 12px; gap: 10px; border-radius: 4px; cursor: default; transition: background 0.2s ease; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                ${avatarHtml}
                <span style="font-size: 0.85rem; color: var(--text-title, #dfdbd2); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                    ${username} ${isCurrentUser ? '(Tú)' : ''}
                </span>
                ${roleText ? `<span style="font-size: 0.7rem; color: var(--accent, #e95420); font-weight: 600; font-family: 'Ubuntu Mono', 'Courier New', monospace;">${roleText}</span>` : ''}
                ${kickButtonHtml}
            </div>
        `;
    });
    
    if (count > 10) {
        html += `
            <div style="padding: 4px 12px; color: var(--text-muted); font-size: 0.7rem; text-align: center; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                +${count - 10} más
            </div>
        `;
    }
    
    container.innerHTML = html;
};

// ============================================================
// RENDERIZAR MENSAJES
// ============================================================

// ============================================================
// RENDERIZAR MENSAJES - CON DESCARGA Y PREVISUALIZACIÓN
// ============================================================

window.renderMessages = function(messages) {
    console.log('📋 renderMessages llamado');
    const container = document.getElementById('messagesArea');
    if (!container) {
        console.warn('⚠️ messagesArea no encontrado');
        return;
    }
    
    if (!Array.isArray(messages) || messages.length === 0) {
        container.innerHTML = `
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
                <h3 style="font-size: 1.2rem; margin-bottom: 8px; color: var(--text-title, #dfdbd2);">No hay mensajes</h3>
                <p style="font-size: 0.9rem;">Sé el primero en enviar un mensaje</p>
            </div>
        `;
        return;
    }
    
    const currentUser = getCurrentUser();
    const currentUserId = currentUser?.id;
    
    container.innerHTML = messages.map(message => {
        const isOwn = message.author?.id === currentUserId;
        const username = message.author?.username || 'Usuario';
        const timestamp = message.created_at ? new Date(message.created_at).toLocaleString() : '';
        const content = message.content || '';
        const messageId = message.id || '';
        const escapedContent = content.replace(/'/g, "\\'");
        
        const attachments = message.attachments || [];
        
        const avatarUrl = message.author?.avatar;
        let avatarHtml = '';
        
        if (avatarUrl) {
            avatarHtml = `
                <img src="${avatarUrl}" 
                     alt="${username}"
                     style="
                        width: 32px;
                        height: 32px;
                        border-radius: 50%;
                        object-fit: cover;
                        flex-shrink: 0;
                        background: var(--accent, #e95420);
                    "
                     onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\\'width:32px;height:32px;border-radius:50%;background:var(--accent,#e95420);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:14px;flex-shrink:0;font-family:\\'Ubuntu Mono\\', \\'Courier New\\', monospace;\\'>${username.charAt(0).toUpperCase()}</div>';"
                >
            `;
        } else {
            avatarHtml = `
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
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                ">
                    ${username.charAt(0).toUpperCase()}
                </div>
            `;
        }
        
        let attachmentsHtml = '';
        if (attachments.length > 0) {
            attachmentsHtml = `
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; font-family: 'Ubuntu Mono', 'Courier New', monospace;">
                    ${attachments.map(attachment => {
                        const fileName = attachment.original_name || attachment.file || 'Archivo';
                        const fileUrl = attachment.file || attachment.url || '';
                        const fileSize = attachment.size ? (attachment.size / 1024).toFixed(1) + ' KB' : '';
                        const isImage = /\.(jpg|jpeg|png|gif|webp|svg|bmp|ico)$/i.test(fileName);
                        
                        if (isImage && fileUrl) {
                            return `
                                <div style="
                                    display: inline-flex;
                                    flex-direction: column;
                                    align-items: center;
                                    background: var(--panel-sidebar, #1a1a1a);
                                    border: 1px solid var(--border-color, #2a2a2a);
                                    border-radius: 6px;
                                    padding: 6px;
                                    max-width: 150px;
                                ">
                                    <img src="${fileUrl}" 
                                         alt="${fileName}"
                                         style="
                                            max-width: 130px;
                                            max-height: 100px;
                                            border-radius: 4px;
                                            object-fit: cover;
                                            cursor: pointer;
                                            transition: transform 0.2s;
                                        "
                                         onmouseover="this.style.transform='scale(1.05)'"
                                         onmouseout="this.style.transform='scale(1)'"
                                         onclick="window.previewImage('${fileUrl}', '${fileName}')"
                                         title="Click para ver imagen"
                                    >
                                    <div style="display: flex; align-items: center; gap: 6px; margin-top: 4px; width: 100%;">
                                        <span style="font-size: 0.6rem; color: var(--text-muted, #888); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: 'Ubuntu Mono', 'Courier New', monospace;">${fileName}</span>
                                        <span style="font-size: 0.6rem; color: var(--text-muted, #888); font-family: 'Ubuntu Mono', 'Courier New', monospace;">${fileSize}</span>
                                        <a href="${fileUrl}" download style="
                                            color: var(--accent, #e95420);
                                            text-decoration: none;
                                            font-size: 0.7rem;
                                            cursor: pointer;
                                            font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                        " title="Descargar archivo">⬇️</a>
                                    </div>
                                </div>
                            `;
                        }
                        
                        const icon = getFileIcon(fileName);
                        return `
                            <div style="
                                display: inline-flex;
                                align-items: center;
                                gap: 8px;
                                background: var(--panel-sidebar, #1a1a1a);
                                border: 1px solid var(--border-color, #2a2a2a);
                                border-radius: 6px;
                                padding: 6px 10px;
                                max-width: 220px;
                            ">
                                <span style="font-size: 1.2rem;">${icon}</span>
                                <span style="font-size: 0.75rem; color: var(--text-title, #dfdbd2); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: 'Ubuntu Mono', 'Courier New', monospace;">${fileName}</span>
                                ${fileSize ? `<span style="font-size: 0.6rem; color: var(--text-muted, #888); font-family: 'Ubuntu Mono', 'Courier New', monospace;">${fileSize}</span>` : ''}
                                <a href="${fileUrl}" download style="
                                    color: var(--accent, #e95420);
                                    text-decoration: none;
                                    font-size: 0.8rem;
                                    cursor: pointer;
                                    transition: transform 0.2s;
                                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                                " onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'" title="Descargar archivo">⬇️</a>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }
        
        return `
            <div class="message ${isOwn ? 'own' : ''}" 
                 data-message-id="${messageId}"
                 style="
                    display: flex;
                    gap: 12px;
                    padding: 12px 16px;
                    margin: 4px 16px;
                    border-radius: 8px;
                    background: ${isOwn ? 'rgba(233,84,32,0.08)' : 'transparent'};
                    border-left: ${isOwn ? '3px solid var(--accent, #e95420)' : 'none'};
                    font-family: 'Ubuntu Mono', 'Courier New', monospace;
                ">
                
                ${avatarHtml}
                
                <div style="flex: 1; min-width: 0;">
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        flex-wrap: wrap;
                        margin-bottom: 4px;
                        font-family: 'Ubuntu Mono', 'Courier New', monospace;
                    ">
                        <span style="
                            font-weight: 600;
                            color: var(--text-title, #dfdbd2);
                            font-size: 0.9rem;
                            font-family: 'Ubuntu Mono', 'Courier New', monospace;
                        ">${username}</span>
                        <span style="
                            color: var(--text-muted, #888);
                            font-size: 0.7rem;
                            font-family: 'Ubuntu Mono', 'Courier New', monospace;
                        ">${timestamp}</span>
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
                                        font-family: 'Ubuntu Mono', 'Courier New', monospace;
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
                                        font-family: 'Ubuntu Mono', 'Courier New', monospace;
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
                    ${content ? `<div style="color: var(--text-body, #dfdbd2); font-size: 0.95rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word; font-family: 'Ubuntu Mono', 'Courier New', monospace;">${content}</div>` : ''}
                    ${attachmentsHtml}
                </div>
            </div>
        `;
    }).join('');
};

// ============================================================
// FUNCIÓN PARA PREVISUALIZAR IMÁGENES (MODAL)
// ============================================================

window.previewImage = function(imageUrl, fileName) {
    console.log('🖼️ Previsualizando imagen:', fileName);
    
    // Remover modal anterior si existe
    const oldModal = document.getElementById('imagePreviewModal');
    if (oldModal) oldModal.remove();
    
    // Crear modal
    const modal = document.createElement('div');
    modal.id = 'imagePreviewModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        cursor: pointer;
        animation: fadeIn 0.3s ease;
        padding: 20px;
    `;
    
    modal.innerHTML = `
        <div style="
            position: relative;
            max-width: 90%;
            max-height: 90%;
            display: flex;
            flex-direction: column;
            align-items: center;
        ">
            <button onclick="this.parentElement.parentElement.remove()" style="
                position: absolute;
                top: -40px;
                right: 0;
                background: none;
                border: none;
                color: #fff;
                font-size: 2rem;
                cursor: pointer;
                z-index: 10;
            ">✕</button>
            <img src="${imageUrl}" 
                 alt="${fileName}"
                 style="
                    max-width: 90vw;
                    max-height: 80vh;
                    border-radius: 8px;
                    object-fit: contain;
                "
            >
            <div style="
                display: flex;
                align-items: center;
                gap: 16px;
                margin-top: 16px;
                color: #fff;
            ">
                <span style="font-size: 0.9rem; color: #aaa;">${fileName}</span>
                <a href="${imageUrl}" download style="
                    color: var(--accent, #e95420);
                    text-decoration: none;
                    font-size: 1.2rem;
                    padding: 8px 16px;
                    border: 1px solid var(--accent, #e95420);
                    border-radius: 4px;
                    transition: all 0.2s;
                " onmouseover="this.style.background='var(--accent, #e95420)'; this.style.color='#fff';" onmouseout="this.style.background='transparent'; this.style.color='var(--accent, #e95420)';">
                    ⬇️ Descargar
                </a>
            </div>
        </div>
    `;
    
    // Cerrar al hacer clic fuera
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.remove();
        }
    });
    
    // Cerrar con Escape
    document.addEventListener('keydown', function closeOnEscape(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('imagePreviewModal');
            if (modal) {
                modal.remove();
                document.removeEventListener('keydown', closeOnEscape);
            }
        }
    });
    
    document.body.appendChild(modal);
    
    // Agregar animación
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
};

// ============================================================
// FUNCIÓN PARA OBTENER ICONO SEGÚN TIPO DE ARCHIVO
// ============================================================

function getFileIcon(fileName) {
    const ext = fileName.split('.').pop().toLowerCase();
    const icons = {
        'pdf': '📄',
        'doc': '📝',
        'docx': '📝',
        'txt': '📃',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'png': '🖼️',
        'gif': '🖼️',
        'svg': '🖼️',
        'webp': '🖼️',
        'bmp': '🖼️',
        'ico': '🖼️',
        'zip': '📦',
        'rar': '📦',
        '7z': '📦',
        'tar': '📦',
        'gz': '📦',
        'mp3': '🎵',
        'wav': '🎵',
        'mp4': '🎬',
        'avi': '🎬',
        'mov': '🎬',
        'exe': '⚙️',
        'msi': '⚙️',
        'apk': '📱',
        'psd': '🎨',
        'ai': '🎨',
        'eps': '🎨',
        'xls': '📊',
        'xlsx': '📊',
        'ppt': '📽️',
        'pptx': '📽️',
        'json': '📋',
        'xml': '📋',
        'html': '🌐',
        'css': '🎨',
        'js': '📜',
        'py': '🐍',
        'java': '☕',
        'cpp': '⚡',
        'c': '⚡',
        'go': '🐹',
        'rs': '🦀'
    };
    return icons[ext] || '📎';
}

// ============================================================
// UPDATE HEADER
// ============================================================

window.updateHeader = function(workspace, channel) {
    console.log('📋 updateHeader:', workspace?.name, channel?.name);
    const nameEl = document.getElementById('workspaceName');
    const descEl = document.getElementById('workspaceDescription');
    const titleEl = document.getElementById('channelTitle');
    const countEl = document.getElementById('messageCount');
    
    if (nameEl && workspace) {
        nameEl.textContent = workspace.name || 'Sin nombre';
        nameEl.style.color = 'var(--text-title, #dfdbd2)';
        nameEl.style.fontSize = '1.1rem';
        nameEl.style.fontWeight = '600';
        //  FUENTE UBUNTU MONO
        nameEl.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
    }
    if (descEl && workspace) {
        descEl.textContent = workspace.description || 'Sin descripción';
        descEl.style.color = 'var(--text-muted, #888)';
        descEl.style.fontSize = '0.8rem';
        //  FUENTE UBUNTU MONO
        descEl.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
    }
    if (titleEl && channel) {
        let channelName = channel.name || 'Canal';
        channelName = channelName.replace(/^#+\s*/, '');
        titleEl.textContent = channelName;
        titleEl.style.color = 'var(--text-title, #dfdbd2)';
        titleEl.style.fontSize = '1rem';
        titleEl.style.fontWeight = '500';
        //  FUENTE UBUNTU MONO
        titleEl.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
    } else if (titleEl) {
        titleEl.textContent = 'Selecciona un canal';
        titleEl.style.color = 'var(--text-muted, #888)';
        titleEl.style.fontSize = '0.9rem';
        titleEl.style.fontWeight = '400';
        //  FUENTE UBUNTU MONO
        titleEl.style.fontFamily = "'Ubuntu Mono', 'Courier New', monospace";
    }
    
    if (countEl) {
        countEl.style.display = 'none';
    }
};

// ============================================================
// EXPONER FUNCIONES GLOBALES
// ============================================================

window.renderWorkspaces = window.renderWorkspaces || renderWorkspaces;
window.renderChannels = window.renderChannels || renderChannels;
window.renderMessages = window.renderMessages || renderMessages;
window.renderWorkspaceMembers = window.renderWorkspaceMembers || renderWorkspaceMembers;
window.updateHeader = window.updateHeader || updateHeader;

console.log('✅ UI cargado');
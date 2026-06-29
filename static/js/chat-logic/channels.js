// static/js/chat-logic/channels.js

// ============================================================
// NOTA: activeChannelId ya está declarado en utils.js
// No lo redeclares aquí, solo úsalo con getters/setters
// ============================================================

// ============================================================
// FUNCIONES DE CANALES
// ============================================================

window.selectChannel = async function(channelId) {
    console.log('📋 selectChannel llamado:', channelId);
    
    if (getActiveChannelId() === channelId) return;
    
    setActiveChannelId(channelId);
    
    // HABILITAR INPUT DE MENSAJE
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.disabled = false;
        messageInput.placeholder = 'Escribe un mensaje...';
        messageInput.focus();
    }
    
    // HABILITAR CLIP
    const clipBtn = document.getElementById('fileUploadBtn');
    if (clipBtn) {
        clipBtn.disabled = false;
    }
    
    // Actualizar UI
    document.querySelectorAll('.channel-item').forEach(el => {
        el.classList.toggle('active', el.dataset.channelId === channelId);
    });
    
    // Cargar mensajes
    try {
        const messages = await fetchMessages(channelId);
        renderMessages(messages);
        
        const countEl = document.getElementById('messageCount');
        if (countEl) {
            countEl.textContent = messages.length + ' mensajes';
        }
        
        const workspace = getActiveWorkspace();
        const channels = await fetchChannels(getActiveWorkspaceId());
        const channel = channels.find(c => c.id === channelId);
        updateHeader(workspace, channel);
        
        const container = document.getElementById('messagesArea');
        if (container) {
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 100);
        }
    } catch (error) {
        console.error('❌ Error al cargar mensajes:', error);
    }
};

// ============================================================
// EXPONER FUNCIONES GLOBALES
// ============================================================

console.log('✅ Channels cargado');
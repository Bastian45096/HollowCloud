// static/js/chat-logic/utils.js

// ============================================================
// ESTADO GLOBAL
// ============================================================

let activeWorkspaceId = null;
let activeChannelId = null;
let workspaces = [];
let currentUser = null;
let editingMessageId = null;
let editingMessageContent = null;
let deletingMessageId = null;
let kickingMemberId = null;
let kickingMemberName = null;

// ============================================================
// GETTERS Y SETTERS - WORKSPACES
// ============================================================

function getActiveWorkspaceId() {
    return activeWorkspaceId;
}

function setActiveWorkspaceId(id) {
    activeWorkspaceId = id;
}

function getActiveChannelId() {
    return activeChannelId;
}

function setActiveChannelId(id) {
    activeChannelId = id;
}

function getWorkspaces() {
    return workspaces;
}

function setWorkspaces(data) {
    workspaces = data;
}

function getActiveWorkspace() {
    if (!activeWorkspaceId) return null;
    return workspaces.find(w => w.id === activeWorkspaceId) || null;
}

// ============================================================
// GETTERS Y SETTERS - USUARIO
// ============================================================

function getCurrentUser() {
    // Si ya hay un usuario guardado, devolverlo
    if (currentUser) {
        return currentUser;
    }
    
    //  Si no, intentar obtener del token JWT
    try {
        const token = localStorage.getItem('access_token');
        if (token) {
            const parts = token.split('.');
            if (parts.length === 3) {
                const payload = JSON.parse(atob(parts[1]));
                const user = {
                    id: payload.user_id || payload.sub || 'unknown',
                    username: payload.username || payload.email || 'Usuario',
                    email: payload.email || '',
                    avatar: payload.avatar || null
                };
                currentUser = user;
 console.log('Usuario obtenido del token:', user);
                return user;
            }
        }
    } catch (e) {
 console.warn('No se pudo decodificar token:', e);
    }
    
    
    return {
        id: 'unknown',
        username: 'Usuario',
        email: '',
        avatar: null
    };
}

function setCurrentUser(user) {
    currentUser = user;
 console.log('Usuario guardado:', currentUser);
}

// ============================================================
// GETTERS Y SETTERS - EDICIÓN
// ============================================================

function getEditingMessageId() {
    return editingMessageId;
}

function setEditingMessageId(id) {
    editingMessageId = id;
}

function getEditingMessageContent() {
    return editingMessageContent;
}

function setEditingMessageContent(content) {
    editingMessageContent = content;
}

function getDeletingMessageId() {
    return deletingMessageId;
}

function setDeletingMessageId(id) {
    deletingMessageId = id;
}

function getKickingMemberId() {
    return kickingMemberId;
}

function setKickingMemberId(id) {
    kickingMemberId = id;
}

function getKickingMemberName() {
    return kickingMemberName;
}

function setKickingMemberName(name) {
    kickingMemberName = name;
}

// ============================================================
// EXPONER FUNCIONES GLOBALES
// ============================================================

window.getActiveWorkspaceId = getActiveWorkspaceId;
window.setActiveWorkspaceId = setActiveWorkspaceId;
window.getActiveChannelId = getActiveChannelId;
window.setActiveChannelId = setActiveChannelId;
window.getWorkspaces = getWorkspaces;
window.setWorkspaces = setWorkspaces;
window.getActiveWorkspace = getActiveWorkspace;
window.getCurrentUser = getCurrentUser;
window.setCurrentUser = setCurrentUser;
window.getEditingMessageId = getEditingMessageId;
window.setEditingMessageId = setEditingMessageId;
window.getEditingMessageContent = getEditingMessageContent;
window.setEditingMessageContent = setEditingMessageContent;
window.getDeletingMessageId = getDeletingMessageId;
window.setDeletingMessageId = setDeletingMessageId;
window.getKickingMemberId = getKickingMemberId;
window.setKickingMemberId = setKickingMemberId;
window.getKickingMemberName = getKickingMemberName;
window.setKickingMemberName = setKickingMemberName;

console.log('Utils cargado');
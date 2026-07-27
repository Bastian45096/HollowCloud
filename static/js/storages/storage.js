/**
 * Storage Client - HollowCloud
 * Manejo exclusivo con JWT.
 * Incluye: Iconos dinámicos personalizados por tipo de archivo y acciones con SVG únicos.
 * CORRECCIÓN: Arreglado el error de appendChild en createCardWithIcon.
 */

const app = (function() {
    let workspaceId = null;
    let currentFolderId = null;
    let folderHistory = [];

    // ============================================================
    // CONFIGURACIÓN Y AUTH
    // ============================================================

    function init(wsId) {
        workspaceId = wsId;
        loadContents(null);
    }

    function getAuthHeaders(isFormData = false) {
        const token = localStorage.getItem('access_token');
        
        if (!token) {
            alert('Sesión expirada. Redirigiendo al login...');
            window.location.href = '/login/';
            throw new Error('No token found');
        }

        const headers = {
            'Authorization': `Bearer ${token}`
        };

        if (!isFormData) {
            headers['Content-Type'] = 'application/json';
        }

        return headers;
    }

    // ============================================================
    // CARGA DE DATOS
    // ============================================================

    async function loadContents(folderId = null) {
        currentFolderId = folderId;
        updateBreadcrumb();
        
        const grid = document.getElementById('contentGrid');
        grid.innerHTML = '<div class="empty-state"><p>Cargando...</p></div>';

        try {
            const url = `/api/storage/${workspaceId}/items/${folderId ? `?folder_id=${folderId}` : ''}`;
            
            const response = await fetch(url, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            if (!response.ok) {
                if (response.status === 401) throw new Error('No autorizado');
                if (response.status === 404) throw new Error('Contenido no encontrado');
                throw new Error('Error al cargar');
            }

            const data = await response.json();
            renderContent(data.folders, data.files);

        } catch (error) {
            console.error(error);
            grid.innerHTML = `<div class="empty-state"><p>Error: ${error.message}</p></div>`;
        }
    }

    // ============================================================
    // RENDERIZADO (CON ICONOS DINÁMICOS PERSONALIZADOS)
    // ============================================================

    function renderContent(folders, files) {
        const grid = document.getElementById('contentGrid');
        grid.innerHTML = '';

        if (folders.length === 0 && files.length === 0) {
            grid.innerHTML = '<div class="empty-state"><p>Esta carpeta está vacía</p></div>';
            return;
        }

        // Render Carpetas
        folders.forEach(folder => {
            const card = createCard('folder', folder.name, folder.created_at, null, () => navigateTo(folder.id, folder.name));
            grid.appendChild(card);
        });

        // Render Archivos
        files.forEach(file => {
            // 1. Obtener el icono dinámico basado en MIME y nombre
            const iconHtml = getFileIcon(file.mime_type, file.name);

            // 2. Crear el contenedor de acciones manualmente para evitar errores de inyección HTML
            const actionsContainer = document.createElement('div');
            actionsContainer.className = 'card-actions';

            // Botón Descargar
            const btnDownload = document.createElement('button');
            btnDownload.className = 'action-btn';
            btnDownload.title = 'Descargar';
            btnDownload.dataset.url = file.url;
            btnDownload.dataset.name = file.name;
            btnDownload.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M7 10L12 15L17 10" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M12 15V3" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            `;
            btnDownload.onclick = (e) => {
                e.stopPropagation();
                downloadFile(btnDownload.dataset.url, btnDownload.dataset.name);
            };

            // Botón Actualizar Versión (Label)
            const labelUpdate = document.createElement('label');
            labelUpdate.className = 'action-btn';
            labelUpdate.title = 'Actualizar Versión';
            // Usamos comillas simples escapadas o dataset para el ID si es necesario, aquí lo dejamos directo en el onchange
            labelUpdate.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 3L12 12" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 3H15" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="12" cy="12" r="2" fill="#F4C430" stroke="#F4C430" stroke-width="1"/>
                </svg>
                <input type="file" hidden onchange="app.uploadVersion('${file.id}', this)">
            `;

            // Botón Reemplazar Total
            const btnReplace = document.createElement('button');
            btnReplace.className = 'action-btn';
            btnReplace.title = 'Reemplazar Archivo (Nombre/Tipo)';
            btnReplace.dataset.id = file.id;
            btnReplace.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M16 3H21V8" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M4 20L21 3" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M21 16V21H16" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M15 15L21 21" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M4 4L9 9" stroke="#F4C430" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            `;
            btnReplace.onclick = (e) => {
                e.stopPropagation();
                openReplaceModal(file.id);
            };

            // Agregamos los botones al contenedor
            actionsContainer.appendChild(btnDownload);
            actionsContainer.appendChild(labelUpdate);
            actionsContainer.appendChild(btnReplace);

            // 3. Crear tarjeta pasando el contenedor de acciones ya construido
            const card = createCardWithIcon('file', file.name, `v${file.version} • ${formatSize(file.size)}`, actionsContainer, null, iconHtml);
            grid.appendChild(card);
        });
    }

    // Función auxiliar para carpetas (usa el SVG por defecto)
    function createCard(type, title, subtitle, actionsElement, onClick) {
        let iconHtml = '';
        if (type === 'folder') {
            iconHtml = `
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink: 0;">
                    <path d="M20 7H12L10 5H4C2.9 5 2 5.9 2 7V19C2 20.1 2.9 21 4 21H20C21.1 21 22 20.1 22 19V9C22 7.9 21.1 7 20 7Z" 
                        fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M12 10V14M12 14L10.5 12.5M12 14L13.5 12.5" 
                        stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.8"/>
                    <circle cx="12" cy="12" r="3" stroke="#E95420" stroke-width="1" stroke-dasharray="1 1" fill="none" opacity="0.6"/>
                </svg>
            `;
        }
        return createCardWithIcon(type, title, subtitle, actionsElement, onClick, iconHtml);
    }

    // Función genérica CORREGIDA para aceptar un Elemento de acciones
    function createCardWithIcon(type, title, subtitle, actionsElement, onClick, iconHtml) {
        const div = document.createElement('div');
        div.className = 'card';
        if (onClick) div.onclick = onClick;
        
        // Estructura base HTML SIEMPRE incluye el div.card-actions vacío por seguridad
        div.innerHTML = `
            <div class="card-actions"></div>
            <div class="icon">${iconHtml}</div>
            <div class="name">${escapeHtml(title)}</div>
            <div class="meta">${subtitle}</div>
        `;

        // Si recibimos un elemento DOM (nodos creados con createElement), lo insertamos ahora
        if (actionsElement instanceof HTMLElement) {
            const actionsContainer = div.querySelector('.card-actions');
            if (actionsContainer) {
                // Limpiamos por si acaso y agregamos
                actionsContainer.innerHTML = ''; 
                // Clonamos los nodos hijos del actionsElement para moverlos correctamente
                Array.from(actionsElement.children).forEach(child => {
                    actionsContainer.appendChild(child.cloneNode(true));
                    
                    // RE-VINCULAR EVENTOS: Al clonar, se pierden los listeners JS (onclick)
                    // Tenemos que reasignarlos manualmente si existen en el original
                    if (child.onclick) {
                        const newChild = actionsContainer.lastElementChild;
                        newChild.onclick = child.onclick;
                    }
                    // Para los inputs dentro de labels, el onchange se mantiene en el HTML string, 
                    // pero si fue creado dinámicamente, hay que tener cuidado. 
                    // En este caso específico, el input de 'uploadVersion' tiene onchange en el innerHTML string, así que funciona.
                    // El botón de descargar y reemplazar tienen onclick asignado por propiedad, así que la línea de arriba los arregla.
                });
            }
        }
        
        return div;
    }

    // ============================================================
    // LÓGICA DE ICONOS PERSONALIZADOS POR TIPO DE ARCHIVO
    // ============================================================

    function getFileIcon(mime, fileName = '') {
        const name = fileName || '';
        const ext = name.split('.').pop().toLowerCase();
        
        // --- PDF ---
        if (ext === 'pdf' || (mime && mime.includes('pdf'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" 
                      fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5" stroke-linejoin="round"/>
                <path d="M14 2V8H20" stroke="#E95420" stroke-width="1.5" stroke-linejoin="round"/>
                <path d="M9 15H15" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
                <path d="M9 18H12" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
                <text x="12" y="12" font-family="monospace" font-size="6" font-weight="bold" fill="#E95420" text-anchor="middle">PDF</text>
            </svg>`;
        }

        // --- IMÁGENES (JPG/JPEG) ---
        if (ext === 'jpeg' || ext === 'jpg' || (mime && mime.includes('image/jpeg'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="18" height="18" rx="3" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
                <path d="M7 14L10.5 10.5L14 14H17L20 10V19H4V16L7 14Z" fill="#E95420" fill-opacity="0.6" stroke="#E95420" stroke-width="1"/>
                <circle cx="16" cy="8" r="2.5" fill="#F4C430" stroke="#F4C430" stroke-width="1"/>
                <path d="M16 5.5V5M16 10.5V11M13.5 8H13M18.5 8H19" stroke="#F4C430" stroke-width="1.5" stroke-linecap="round"/>
            </svg>`;
        }

        // --- IMÁGENES (PNG) ---
        if (ext === 'png' || (mime && mime.includes('image/png'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="18" height="18" rx="3" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
                <circle cx="9" cy="9" r="2" fill="#F4C430" stroke="#F4C430" stroke-width="1"/>
                <path d="M15 15L18 18M18 15L15 18" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
                <path d="M7 17L10 14L13 17L16 14L19 17" stroke="#E95420" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>`;
        }

        // --- WORD / DOCUMENTOS ---
        if (ext === 'doc' || ext === 'docx' || (mime && mime.includes('word')) || (mime && mime.includes('document'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
                <path d="M14 2V8H20" stroke="#E95420" stroke-width="1.5"/>
                <path d="M8 13H16M8 16H14" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
                <text x="12" y="12" font-family="monospace" font-size="6" font-weight="bold" fill="#E95420" text-anchor="middle">DOC</text>
            </svg>`;
        }

        // --- EXCEL / HOJAS DE CÁLCULO ---
        if (ext === 'xls' || ext === 'xlsx' || (mime && mime.includes('excel')) || (mime && mime.includes('spreadsheet'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
                <path d="M14 2V8H20" stroke="#E95420" stroke-width="1.5"/>
                <path d="M8 12H16M8 16H16M12 8V16" stroke="#E95420" stroke-width="1.5" stroke-linecap="round"/>
                <rect x="9" y="13" width="6" height="4" rx="1" fill="#F4C430" opacity="0.6"/>
            </svg>`;
        }

        // --- ZIP / COMPRIMIDOS ---
        if (ext === 'zip' || ext === 'rar' || ext === '7z' || (mime && mime.includes('zip')) || (mime && mime.includes('compressed'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 7C4 5.89543 4.89543 5 6 5H18C19.1046 5 20 5.89543 20 7V19C20 20.1046 19.1046 21 18 21H6C4.89543 21 4 20.1046 4 19V7Z" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
                <path d="M9 5V7M15 5V7" stroke="#E95420" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="12" cy="14" r="2.5" fill="#F4C430" stroke="#F4C430" stroke-width="1"/>
                <path d="M12 12.5V15.5M10.5 14H13.5" stroke="#111111" stroke-width="1.5" stroke-linecap="round"/>
            </svg>`;
        }

        // --- VIDEO ---
        if (ext === 'mp4' || ext === 'avi' || ext === 'mkv' || ext === 'mov' || (mime && mime.includes('video'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="5" width="18" height="14" rx="2" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
                <path d="M10 9L15 12L10 15V9Z" fill="#E95420" stroke="#E95420" stroke-width="1.5" stroke-linejoin="round"/>
                <circle cx="12" cy="12" r="6" stroke="#F4C430" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
            </svg>`;
        }

        // --- AUDIO ---
        if (ext === 'mp3' || ext === 'wav' || ext === 'ogg' || (mime && mime.includes('audio'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 18V5L20 3V16" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="7" cy="18" r="3" fill="rgba(233, 84, 32, 0.2)" stroke="#E95420" stroke-width="1.5"/>
                <circle cx="18" cy="16" r="3" fill="rgba(244, 196, 48, 0.2)" stroke="#F4C430" stroke-width="1.5"/>
                <path d="M15 8L18 6" stroke="#F4C430" stroke-width="1.5" stroke-linecap="round"/>
            </svg>`;
        }

        // --- TEXTO PLANO ---
        if (ext === 'txt' || (mime && mime.includes('text'))) {
            return `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
                <path d="M14 2V8H20" stroke="#E95420" stroke-width="1.5"/>
                <path d="M8 12H16M8 15H14" stroke="#E95420" stroke-width="2" stroke-linecap="round"/>
            </svg>`;
        }

        // --- DEFAULT (Generic File) ---
        return `
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="rgba(233, 84, 32, 0.1)" stroke="#E95420" stroke-width="1.5"/>
            <path d="M14 2V8H20" stroke="#E95420" stroke-width="1.5"/>
            <path d="M12 12V16M12 16L10.5 14.5M12 16L13.5 14.5" stroke="#E95420" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`;
    }

    // ============================================================
    // NAVEGACIÓN
    // ============================================================

    function navigateTo(folderId, folderName) {
        folderHistory.push({ id: folderId, name: folderName });
        loadContents(folderId);
    }

    function updateBreadcrumb() {
        const bc = document.getElementById('breadcrumb');
        let html = `<span class="breadcrumb-item" onclick="app.goToRoot()">Raíz</span>`;
        
        folderHistory.forEach((item, index) => {
            html += `<span class="separator">/</span>`;
            if (index === folderHistory.length - 1) {
                html += `<span class="breadcrumb-item active">${escapeHtml(item.name)}</span>`;
            } else {
                html += `<span class="breadcrumb-item" onclick="app.goToStep(${index})">${escapeHtml(item.name)}</span>`;
            }
        });
        bc.innerHTML = html;
    }

    function goToRoot() {
        folderHistory = [];
        loadContents(null);
    }

    function goToStep(index) {
        folderHistory = folderHistory.slice(0, index + 1);
        loadContents(folderHistory[index].id);
    }

    // ============================================================
    // ACCIONES: CARPETAS
    // ============================================================

    function openCreateFolderModal() {
        const modal = document.getElementById('folderModal');
        const input = document.getElementById('folderNameInput');
        if(modal) modal.classList.add('active');
        if(input) {
            input.value = '';
            input.focus();
        }
    }

    function closeModal() {
        const modal = document.getElementById('folderModal');
        const input = document.getElementById('folderNameInput');
        if(modal) modal.classList.remove('active');
        if(input) input.value = '';
    }

    async function createFolder() {
        const input = document.getElementById('folderNameInput');
        const name = input ? input.value.trim() : '';
        
        if (!name) return alert('El nombre no puede estar vacío');

        try {
            const payload = { name: name };
            if (currentFolderId) payload.parent_id = currentFolderId;

            const response = await fetch(`/api/storage/${workspaceId}/folders/`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Error al crear');
            }

            closeModal();
            loadContents(currentFolderId);
        } catch (error) {
            alert(error.message);
        }
    }

    // ============================================================
    // ACCIONES: ARCHIVOS
    // ============================================================

    async function handleFileUpload(input) {
        if (!input.files[0]) return;
        const formData = new FormData();
        formData.append('file', input.files[0]);
        if (currentFolderId) formData.append('folder_id', currentFolderId);

        await performUpload(`/api/storage/${workspaceId}/upload/`, formData, input);
    }

    async function uploadVersion(fileId, input) {
        if (!input.files[0]) return;
        const formData = new FormData();
        formData.append('file', input.files[0]);

        await performUpload(`/api/storage/${workspaceId}/files/${fileId}/versions/`, formData, input);
    }

    async function performUpload(url, formData, inputElement) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Error en la subida');
            }

            inputElement.value = '';
            loadContents(currentFolderId);
        } catch (error) {
            alert(error.message);
        }
    }

    // --- Lógica de Reemplazo Total ---
    
    function openReplaceModal(fileId) {
        const replaceInput = document.getElementById('replaceFileInput');
        if(!replaceInput) return;
        
        replaceInput.dataset.targetId = fileId;
        replaceInput.value = ''; 
        
        const fileNameSpan = document.getElementById('replaceFileName');
        if(fileNameSpan) fileNameSpan.textContent = 'Seleccionar archivo...';
        
        const modal = document.getElementById('replaceFileModal');
        if(modal) modal.classList.add('active');
    }

    function closeReplaceModal() {
        const modal = document.getElementById('replaceFileModal');
        if(modal) modal.classList.remove('active');
    }

    async function confirmReplaceFile() {
        const input = document.getElementById('replaceFileInput');
        const fileId = input ? input.dataset.targetId : null;
        
        if (!input || !input.files[0]) return alert('Selecciona un archivo primero');
        if (!fileId) return alert('Error: No hay archivo seleccionado para reemplazar');

        const formData = new FormData();
        formData.append('file', input.files[0]);

        try {
            const response = await fetch(`/api/storage/${workspaceId}/files/${fileId}/replace/`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Error al reemplazar');
            }

            closeReplaceModal();
            loadContents(currentFolderId);
        } catch (error) {
            alert(error.message);
        }
    }

    function downloadFile(url, filename) {
        if (!url) return alert('URL no disponible');
        window.open(url, '_blank');
    }

    // ============================================================
    // UTILIDADES
    // ============================================================

    function formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Exportar funciones públicas internas
    return {
        init,
        openCreateFolderModal,
        closeModal,
        createFolder,
        handleFileUpload,
        uploadVersion,
        downloadFile,
        goToRoot,
        goToStep,
        openReplaceModal,
        closeReplaceModal,
        confirmReplaceFile
    };

})();

// ============================================================
// EXPORTAR A WINDOW PARA QUE FUNCIONE EL HTML
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    if (window.STORAGE_WORKSPACE_ID) {
        app.init(window.STORAGE_WORKSPACE_ID);
    }

    window.app = app;
    
    // Exponer funciones individuales
    window.openCreateFolderModal = app.openCreateFolderModal;
    window.closeModal = app.closeModal;
    window.createFolder = app.createFolder;
    window.handleFileUpload = app.handleFileUpload;
    window.uploadVersion = app.uploadVersion;
    window.downloadFile = app.downloadFile;
    window.goToRoot = app.goToRoot;
    window.goToStep = app.goToStep;
    
    // Exponer funciones de reemplazo
    window.openReplaceModal = app.openReplaceModal;
    window.closeReplaceModal = app.closeReplaceModal;
    window.confirmReplaceFile = app.confirmReplaceFile;
});
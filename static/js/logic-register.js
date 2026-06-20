// register.js - Lógica completa para el registro en HollowCloud

const form = document.getElementById('registerForm');
const btn = document.getElementById('registerBtn');
const errorMsg = document.getElementById('errorMessage');
const successMsg = document.getElementById('successMessage');

// Variables para el cropper
let cropperInstance = null;
let selectedFile = null;
let isCropped = false;

// Función para mostrar error de campo
function showFieldError(fieldId, message) {
    const errorEl = document.getElementById(fieldId + 'Error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('show');
    }
}

// Función para mostrar error general
function showError(message) {
    errorMsg.textContent = '❌ ' + message;
    errorMsg.classList.add('show');
    successMsg.classList.remove('show');
}

// Función para mostrar éxito
function showSuccess(message) {
    successMsg.textContent = '✅ ' + message;
    successMsg.classList.add('show');
    errorMsg.classList.remove('show');
}

// Validación de contraseña: debe tener letras, números y caracteres especiales
function validatePasswordStrength(password) {
    const hasLetters = /[a-zA-Z]/.test(password);
    const hasNumbers = /[0-9]/.test(password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    const hasMinLength = password.length >= 8;
    
    return {
        isValid: hasLetters && hasNumbers && hasSpecial && hasMinLength,
        hasLetters,
        hasNumbers,
        hasSpecial,
        hasMinLength
    };
}

// Función para actualizar el hint de la contraseña en tiempo real
function updatePasswordHint(password) {
    const hint = document.getElementById('passwordHint');
    const validation = validatePasswordStrength(password);
    
    if (password.length === 0) {
        hint.innerHTML = 'Mínimo 8 caracteres, con letras, números y caracteres especiales (!@#$%^&*)';
        hint.style.color = '#6c727a';
        return;
    }
    
    let requirements = [];
    
    if (!validation.hasMinLength) {
        requirements.push('<span style="color:#C91D04;">✗ mínimo 8 caracteres</span>');
    } else {
        requirements.push('<span style="color:#00ff66;">✓ 8 caracteres</span>');
    }
    
    if (!validation.hasLetters) {
        requirements.push('<span style="color:#C91D04;">✗ letras</span>');
    } else {
        requirements.push('<span style="color:#00ff66;">✓ letras</span>');
    }
    
    if (!validation.hasNumbers) {
        requirements.push('<span style="color:#C91D04;">✗ números</span>');
    } else {
        requirements.push('<span style="color:#00ff66;">✓ números</span>');
    }
    
    if (!validation.hasSpecial) {
        requirements.push('<span style="color:#C91D04;">✗ caracteres especiales</span>');
    } else {
        requirements.push('<span style="color:#00ff66;">✓ caracteres especiales</span>');
    }
    
    hint.innerHTML = requirements.join(' | ');
    hint.style.color = '#cfd1d4';
}

// Inicializar cropper al seleccionar imagen
document.getElementById('avatar').addEventListener('change', function(e) {
    const file = this.files[0];
    
    if (!file) {
        cancelCrop();
        return;
    }

    // Validar tamaño (máx 5MB)
    if (file.size > 5 * 1024 * 1024) {
        showFieldError('avatar', 'La imagen no debe superar los 5MB');
        this.value = '';
        cancelCrop();
        return;
    }
    
    // Validar tipo
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showFieldError('avatar', 'Formato no soportado. Usa JPG, PNG, GIF o WEBP');
        this.value = '';
        cancelCrop();
        return;
    }

    // Guardar el archivo seleccionado
    selectedFile = file;

    // Mostrar preview
    const reader = new FileReader();
    reader.onload = function(e) {
        const cropImage = document.getElementById('cropImage');
        cropImage.src = e.target.result;

        // Mostrar wrapper de recorte
        document.getElementById('cropWrapper').style.display = 'block';

        // Destruir cropper anterior si existe
        if (cropperInstance) {
            cropperInstance.destroy();
        }

        // Inicializar cropper
        cropperInstance = new Cropper(cropImage, {
            aspectRatio: 1,
            viewMode: 1,
            background: false,
            responsive: true,
            autoCropArea: 1,
            dragMode: 'move',
            cropBoxResizable: true,
            cropBoxMovable: true
        });
    };
    reader.readAsDataURL(file);
});

// Confirmar recorte
function confirmCrop() {
    if (!cropperInstance) return;

    // Obtener canvas recortado
    const canvas = cropperInstance.getCroppedCanvas({ width: 300, height: 300 });
    
    // Convertir a blob
    canvas.toBlob(function(blob) {
        // Crear nuevo archivo con el blob recortado
        const croppedFile = new File([blob], selectedFile.name, {
            type: 'image/jpeg',
            lastModified: Date.now()
        });

        // Reemplazar el archivo en el input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(croppedFile);
        document.getElementById('avatar').files = dataTransfer.files;

        // Actualizar preview
        const preview = document.getElementById('avatarPreview');
        const container = document.getElementById('avatarContainer');
        preview.src = URL.createObjectURL(blob);
        container.classList.add('has-image');
        isCropped = true;

        // Ocultar cropper
        document.getElementById('cropWrapper').style.display = 'none';
        
        // Limpiar error
        document.getElementById('avatarError').classList.remove('show');

        // Destruir cropper
        if (cropperInstance) {
            cropperInstance.destroy();
            cropperInstance = null;
        }
    }, 'image/jpeg', 0.9);
}

// Cancelar recorte
function cancelCrop() {
    if (cropperInstance) {
        cropperInstance.destroy();
        cropperInstance = null;
    }
    document.getElementById('cropWrapper').style.display = 'none';
    document.getElementById('avatar').value = '';
    document.getElementById('avatarPreview').src = '';
    document.getElementById('avatarContainer').classList.remove('has-image');
    selectedFile = null;
    isCropped = false;
}

// Limpiar errores al escribir
document.querySelectorAll('input, textarea').forEach(el => {
    el.addEventListener('input', function() {
        this.classList.remove('error');
        const errorEl = document.getElementById(this.id + 'Error');
        if (errorEl) {
            errorEl.classList.remove('show');
        }
    });
});

// ============================================================
// VALIDACIÓN EN TIEMPO REAL DE LA CONTRASEÑA
// ============================================================
document.getElementById('password').addEventListener('input', function() {
    const password = this.value;
    
    // Actualizar el hint visual
    updatePasswordHint(password);
    
    // Mostrar/ocultar error en el campo
    const errorEl = document.getElementById('passwordError');
    const validation = validatePasswordStrength(password);
    
    if (password.length > 0 && !validation.isValid) {
        let messages = [];
        if (!validation.hasMinLength) messages.push('mínimo 8 caracteres');
        if (!validation.hasLetters) messages.push('letras');
        if (!validation.hasNumbers) messages.push('números');
        if (!validation.hasSpecial) messages.push('caracteres especiales (!@#$%^&*)');
        
        errorEl.textContent = 'La contraseña debe tener: ' + messages.join(', ');
        errorEl.classList.add('show');
    } else if (password.length > 0 && validation.isValid) {
        errorEl.textContent = '✅ Contraseña válida';
        errorEl.style.color = '#00ff66';
        errorEl.classList.add('show');
    } else {
        errorEl.classList.remove('show');
    }
});

// También validar cuando se confirma la contraseña
document.getElementById('password_confirm').addEventListener('input', function() {
    const password = document.getElementById('password').value;
    const confirm = this.value;
    const errorEl = document.getElementById('passwordConfirmError');
    
    if (confirm.length > 0 && password !== confirm) {
        errorEl.textContent = 'Las contraseñas no coinciden';
        errorEl.classList.add('show');
    } else if (confirm.length > 0 && password === confirm) {
        errorEl.textContent = '✅ Contraseñas coinciden';
        errorEl.style.color = '#00ff66';
        errorEl.classList.add('show');
    } else {
        errorEl.classList.remove('show');
    }
});

// ============================================================
// ENVÍO DEL FORMULARIO - CON EL ENDPOINT CORRECTO
// ============================================================
form.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Resetear mensajes
    errorMsg.classList.remove('show');
    successMsg.classList.remove('show');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Creando cuenta...';

    // Validar avatar (obligatorio)
    const avatarFile = document.getElementById('avatar').files[0];
    if (!avatarFile) {
        showFieldError('avatar', 'La foto de perfil es obligatoria');
        btn.disabled = false;
        btn.innerHTML = 'Crear cuenta';
        return;
    }

    // Validar contraseñas
    const password = document.getElementById('password').value;
    const passwordConfirm = document.getElementById('password_confirm').value;

    if (password !== passwordConfirm) {
        showError('Las contraseñas no coinciden');
        btn.disabled = false;
        btn.innerHTML = 'Crear cuenta';
        return;
    }

    if (password.length < 8) {
        showError('La contraseña debe tener al menos 8 caracteres');
        btn.disabled = false;
        btn.innerHTML = 'Crear cuenta';
        return;
    }

    // Validar fortaleza de contraseña
    const passwordValidation = validatePasswordStrength(password);
    if (!passwordValidation.isValid) {
        let messages = [];
        if (!passwordValidation.hasMinLength) messages.push('mínimo 8 caracteres');
        if (!passwordValidation.hasLetters) messages.push('letras');
        if (!passwordValidation.hasNumbers) messages.push('números');
        if (!passwordValidation.hasSpecial) messages.push('caracteres especiales (!@#$%^&*)');
        
        showError('La contraseña debe tener: ' + messages.join(', '));
        btn.disabled = false;
        btn.innerHTML = 'Crear cuenta';
        return;
    }

    // Crear FormData
    const formData = new FormData();
    formData.append('username', document.getElementById('username').value.trim());
    formData.append('email', document.getElementById('email').value.trim());
    formData.append('password', password);
    formData.append('password2', passwordConfirm);
    formData.append('avatar', avatarFile);
    
    const bio = document.getElementById('bio').value.trim();
    if (bio) {
        formData.append('bio', bio);
    }

    try {
        // ✅ ENDPOINT CORRECTO - Usando la URL de tu RegisterView
        const response = await fetch('/api/APIVIEWCRTA/', {
            method: 'POST',
            body: formData
            // NO pongas Content-Type, el navegador lo pone automáticamente con FormData
        });

        const data = await response.json();

        if (response.ok) {
            // Éxito - mostrar mensaje y redirigir
            showSuccess('¡Cuenta creada exitosamente! Redirigiendo al login...');
            
            setTimeout(() => {
                window.location.href = '/login/';
            }, 2000);
        } else {
            // Error del servidor - mostrar mensaje
            let errorText = 'Error al crear la cuenta.';
            
            if (data.errors) {
                // Errores de validación del serializer
                const firstError = Object.values(data.errors)[0];
                if (Array.isArray(firstError)) {
                    errorText = firstError[0];
                } else if (typeof firstError === 'string') {
                    errorText = firstError;
                } else {
                    errorText = JSON.stringify(data.errors);
                }
            } else if (data.message) {
                errorText = data.message;
            } else if (data.detail) {
                errorText = data.detail;
            }
            
            showError(errorText);
            
            // Mostrar errores por campo específico
            if (data.errors) {
                if (data.errors.avatar) {
                    showFieldError('avatar', data.errors.avatar[0]);
                }
                if (data.errors.username) {
                    showFieldError('username', data.errors.username[0]);
                }
                if (data.errors.email) {
                    showFieldError('email', data.errors.email[0]);
                }
                if (data.errors.password) {
                    showFieldError('password', data.errors.password[0]);
                }
                if (data.errors.password_confirm) {
                    showFieldError('password_confirm', data.errors.password_confirm[0]);
                }
            }
        }
    } catch (err) {
        // Error de red o conexión
        showError('Error de conexión. Verifica tu conexión a internet.');
        console.error('Error:', err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Crear cuenta';
    }
});

// Funciones globales para el HTML (onclick)
window.confirmCrop = confirmCrop;
window.cancelCrop = cancelCrop;
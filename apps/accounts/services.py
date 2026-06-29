# apps/accounts/services.py

"""
Servicios de la aplicación accounts.

Los servicios contienen la lógica de negocio de la aplicación.
Cada función representa una operación de negocio específica.

Principios aplicados:
- Single Responsibility: cada servicio hace una cosa
- Separation of Concerns: la lógica de negocio está separada de las vistas
- Transaction Atomic: las operaciones que modifican datos son atómicas

Responsabilidades de los servicios:
1. Crear usuarios (create_user)
2. Autenticar usuarios (authenticate_user, login_user)
3. Generar tokens (generate_tokens, refresh_access_token)
4. Cerrar sesión (logout_user)
5. Actualizar perfil (update_profile)
6. Cambiar contraseña (change_password)
7. Verificar cuenta (verify_user)
8. Activar/Desactivar cuenta (activate_user, deactivate_user)
"""

from __future__ import annotations
import logging
from re import I
from typing import Any, Optional, Dict
from django.core.cache import cache

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
import time
import hashlib

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from apps.accounts.models import User, Profile

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTES DE CACHE Y RATE LIMITING
# ============================================================

# Cache negativa: bloquea emails que no existen por 5 minutos
# Esto evita ataques de fuerza bruta intentando adivinar emails
CACHE_NEGATIVE_TTL = 300  # 5 minutos
CACHE_NEGATIVE_PREFIX = "user_not_found"

# Rate limiting: límite de intentos de login
MAX_ATTEMPTS_IP = 10  # Máximo 10 intentos por IP
MAX_ATTEMPTS_EMAIL = 5  # Máximo 5 intentos por email
RATE_LIMIT_WINDOW = 300  # Ventana de 5 minutos

# Protección contra timing attacks
# Hace que todas las respuestas de login tarden lo mismo
TIMING_ATTACK_SLEEP = 0.1  # 100ms


# ============================================================
# FUNCIONES AUXILIARES DE CACHE
# ============================================================

def _get_negative_cache_key(email: str) -> str:
    """Genera la clave de cache para emails bloqueados."""
    return f"{CACHE_NEGATIVE_PREFIX}:{email.lower()}"


def _is_user_blocked(email: str) -> bool:
    """Verifica si un email está bloqueado por cache negativa."""
    cache_key = _get_negative_cache_key(email)
    return cache.get(cache_key, False)


def _block_user(email: str) -> None:
    """Bloquea un email en cache negativa por 5 minutos."""
    cache_key = _get_negative_cache_key(email)
    cache.set(cache_key, True, CACHE_NEGATIVE_TTL)


def _unblock_user(email: str) -> None:
    """Desbloquea un email de cache negativa."""
    cache_key = _get_negative_cache_key(email)
    cache.delete(cache_key)


def _get_rate_limit_key_ip(request) -> str:
    """Genera la clave de rate limiting por IP del cliente."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')
    ip = ip or 'unknown_ip'
    return f"login_attempts_ip:{ip}"


def _get_rate_limit_key_email(email: str) -> str:
    """Genera la clave de rate limiting por email."""
    return f"login_attempts_email:{email.lower()}"


def _check_rate_limit(key: str, max_attempts: int, window: int = RATE_LIMIT_WINDOW) -> bool:
    """Verifica si se excedió el límite de intentos."""
    attempts = cache.get(key, 0)
    return attempts < max_attempts  # True si no se excedió, False si está bloqueado


def _increment_rate_limit(key: str, window: int = RATE_LIMIT_WINDOW) -> None:
    """Incrementa el contador de intentos fallidos."""
    attempts = cache.get(key, 0)
    cache.set(key, attempts + 1, window)


def _reset_rate_limit(key: str) -> None:
    """Resetea el contador de intentos (login exitoso)."""
    cache.delete(key)


def _get_cached_user(email: str) -> Optional[User]:
    """Obtiene un usuario de cache positiva (1 hora)."""
    cache_key = f"user_authenticated:{email.lower()}"
    user_id = cache.get(cache_key)
    
    if user_id:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            cache.delete(cache_key)
            return None
    return None


def _set_cached_user(user: User) -> None:
    """Guarda un usuario en cache positiva (1 hora)."""
    cache_key = f"user_authenticated:{user.email.lower()}"
    cache.set(cache_key, user.id, 3600)  # 1 hora


def _check_account_status(user: User) -> None:
    """Verifica el estado de la cuenta (activa y verificada)."""
    if not user.is_active:
        raise ValidationError("Tu cuenta ha sido desactivada. Contacta a soporte.")
    
    if not user.is_verified:
        raise ValidationError("Tu cuenta no está verificada. Revisa tu email.")


# ============================================================
# SERVICIOS DE AUTENTICACIÓN
# ============================================================

def generate_tokens(user: User) -> dict[str, str]:
    """
    Genera un par de tokens JWT (access + refresh) para un usuario autenticado.
    
    Flujo:
    1. Crear refresh token con RefreshToken.for_user()
    2. Obtener access token del refresh token
    3. Retornar ambos tokens como strings
    
    Uso: Después de login o registro exitoso.
    """
    # Crea el refresh token
    refresh = RefreshToken.for_user(user)
    
    # Obtiene el access token como string
    access = str(refresh.access_token)
    
    # Obtiene el refresh token como string
    refresh_str = str(refresh)
    
    return {
        "access": access,
        "refresh": refresh_str,
    }


def refresh_access_token(*, refresh_token: str) -> dict[str, str]:
    """
    Genera un nuevo access token a partir de un refresh token válido.
    
    Flujo:
    1. Validar que el refresh token exista
    2. Cargar el refresh token
    3. Generar nuevo access token
    4. Retornar el nuevo access token
    
    Uso: Cuando el access token expira, se usa el refresh token para obtener uno nuevo.
    """
    if not refresh_token:
        raise ValidationError("Refresh token es requerido")

    try:
        # Carga el refresh token
        refresh = RefreshToken(refresh_token)
        
        # Genera nuevo access token
        access_token = str(refresh.access_token)
        
        return {
            "access": access_token,
        }

    except TokenError:
        raise ValidationError("Refresh token inválido o expirado")
    except Exception:
        raise


def logout_user(*, refresh_token: str) -> None:
    """
    Cierra la sesión de un usuario invalidando su refresh token.
    
    Flujo:
    1. Validar que el refresh token exista
    2. Cargar el refresh token
    3. Agregar el token a la blacklist (invalidarlo)
    
    Uso: Cuando un usuario cierra sesión manualmente.
    """
    if not refresh_token:
        return

    try:
        # Carga el refresh token
        token = RefreshToken(refresh_token)
        
        # Invalida el token (blacklist)
        token.blacklist()

    except TokenError:
        # Si el token ya es inválido, no hacemos nada
        pass
    except Exception:
        raise


# ============================================================
# SERVICIOS DE AUTENTICACIÓN CON RATE LIMITING
# ============================================================

def authenticate_user(*, email: str, password: str, request=None) -> User:
    """
    Autentica a un usuario con validaciones de seguridad.
    
    Capas de seguridad:
    1. Cache negativa: bloquea emails inexistentes por 5 minutos
    2. Cache positiva: usuarios autenticados por 1 hora
    3. Rate limiting: por IP y por email
    4. Protección timing attack: todas las respuestas tardan lo mismo
    
    Flujo:
    1. Validar entrada (email y password no vacíos)
    2. Verificar cache negativa (¿email bloqueado?)
    3. Verificar rate limits (¿demasiados intentos?)
    4. Verificar cache positiva (¿usuario ya autenticado?)
    5. Autenticar con Django authenticate()
    6. Si éxito: resetear rate limits, guardar en cache
    7. Si falla: incrementar rate limits, bloquear si no existe
    
    Uso: En el LoginView y en el servicio login_user.
    """
    email = email.strip().lower()
    password = password.strip() if password else ''

    # 1. VALIDACIÓN DE ENTRADA
    if not email or not password:
        raise ValidationError("Credenciales inválidas")

    # 2. CACHE NEGATIVA - ¿Email bloqueado?
    if _is_user_blocked(email):
        raise ValidationError("Credenciales inválidas")

    # 3. RATE LIMITING
    client_ip = "0.0.0.0"
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            client_ip = x_forwarded.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

    ip_key = _get_rate_limit_key_ip(request) if request else None
    email_key = _get_rate_limit_key_email(email)

    # Verificar IP
    if ip_key and not _check_rate_limit(ip_key, MAX_ATTEMPTS_IP):
        raise ValidationError("Demasiados intentos. Espera 5 minutos.")

    # Verificar email
    if not _check_rate_limit(email_key, MAX_ATTEMPTS_EMAIL):
        raise ValidationError("Demasiados intentos. Espera 5 minutos.")

    # 4. CACHE POSITIVA - ¿Usuario ya autenticado?
    cached_user = _get_cached_user(email)
    if cached_user and cached_user.check_password(password):
        return cached_user

    # 5. TIMING ATTACK PROTECTION
    auth_start = time.time()

    try:
        # 6. AUTENTICACIÓN
        user = authenticate(username=email, password=password)

        if user is not None:
            # 7. LOGIN EXITOSO
            
            # Verificar cuenta activa
            if not user.is_active:
                raise ValidationError("Credenciales inválidas")
            
            # Resetear rate limits
            if ip_key:
                _reset_rate_limit(ip_key)
            _reset_rate_limit(email_key)
            
            # Guardar en cache positiva
            _set_cached_user(user)
            
            # Desbloquear de cache negativa (si estaba bloqueado)
            _unblock_user(email)
            
            return user

        # 8. LOGIN FALLIDO
        
        # Incrementar rate limits
        if ip_key:
            _increment_rate_limit(ip_key)
        _increment_rate_limit(email_key)
        
        # Verificar si el usuario existe
        from .selectors import get_user_by_email
        try:
            user_exists = get_user_by_email(email=email, use_cache=False)
        except:
            user_exists = None
        
        # Si no existe, bloquear en cache negativa
        if not user_exists:
            _block_user(email)

        # 9. TIMING ATTACK MITIGATION
        # Dormir para que las respuestas de éxito y fallo tarden lo mismo
        elapsed = time.time() - auth_start
        if elapsed < TIMING_ATTACK_SLEEP:
            time.sleep(TIMING_ATTACK_SLEEP - elapsed)
        
        raise ValidationError("Credenciales inválidas")

    except ValidationError:
        raise
    except Exception:
        raise ValidationError("Error al autenticar. Intenta nuevamente.")


def login_user(*, email: str, password: str, request=None) -> Dict[str, Any]:
    """
    Inicia sesión de un usuario y devuelve usuario + tokens.
    
    Combina authenticate_user + generate_tokens + actualización de last_login.
    
    Flujo:
    1. Validar entrada
    2. Autenticar usuario (con authenticate_user)
    3. Si éxito: actualizar last_login, generar tokens
    4. Retornar usuario + tokens
    
    Uso: En el LoginView.
    """
    email = email.strip().lower() if email else ''
    password = password.strip() if password else ''

    # 1. VALIDACIÓN DE ENTRADA
    if not email or not password:
        raise ValidationError("Email y contraseña son requeridos")

    # 2. CACHE NEGATIVA - ¿Usuario bloqueado?
    if _is_user_blocked(email):
        raise ValidationError("Credenciales inválidas")

    # 3. RATE LIMITING
    ip_key = _get_rate_limit_key_ip(request) if request else None 
    email_key = _get_rate_limit_key_email(email)  

    if ip_key and not _check_rate_limit(ip_key, MAX_ATTEMPTS_IP): 
        raise ValidationError("Demasiados intentos desde esta IP. Espera 5 minutos.")

    if not _check_rate_limit(email_key, MAX_ATTEMPTS_EMAIL): 
        raise ValidationError("Demasiados intentos para este email. Espera 5 minutos.")

    # 4. CACHE POSITIVA - ¿Usuario ya autenticado?
    cached_user = _get_cached_user(email)  
    if cached_user and cached_user.check_password(password):
        # Actualizar last_login
        cached_user.last_login = timezone.now()
        cached_user.save(update_fields=["last_login"])
        
        return {
            "user": cached_user,
            "tokens": generate_tokens(user=cached_user),
        }

    # 5. TIMING ATTACK PROTECTION
    start_time = time.time()

    try:
        # 6. AUTENTICACIÓN
        user = authenticate(request, email=email, password=password)

        if user is not None:
            # 7. LOGIN EXITOSO
            
            # Resetear rate limits
            if ip_key:
                _reset_rate_limit(ip_key)  
            _reset_rate_limit(email_key)  

            # Guardar en cache positiva
            _set_cached_user(user) 
            
            # Desbloquear de cache negativa
            _unblock_user(email)  

            # Actualizar last_login
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            # Generar tokens
            tokens = generate_tokens(user=user)

            return {
                "user": user,
                "tokens": tokens,
            }

        # 8. LOGIN FALLIDO
        
        # Incrementar rate limits
        if ip_key:
            _increment_rate_limit(ip_key) 
        _increment_rate_limit(email_key) 

        # Verificar si el usuario existe
        try:
            from .selectors import get_user_by_email
            user_exists = get_user_by_email(email=email, use_cache=False)
        except:
            user_exists = None

        # Si no existe, bloquear en cache negativa
        if not user_exists:
            _block_user(email) 

        # 9. TIMING ATTACK MITIGATION
        elapsed = time.time() - start_time
        if elapsed < TIMING_ATTACK_SLEEP:
            time.sleep(TIMING_ATTACK_SLEEP - elapsed)

        raise ValidationError("Credenciales inválidas")

    except ValidationError:
        raise
    except Exception:
        raise ValidationError("Error al iniciar sesión. Intenta nuevamente.")


# ============================================================
# SERVICIOS DE USUARIO
# ============================================================

@transaction.atomic
def create_user(
    *,
    email: str,
    username: str,
    password: str,
    first_name: str = '',
    last_name: str = '',
    bio: str = '',
    avatar: Any = None,
) -> User:
    """
    Crea un nuevo usuario en la plataforma.
    
    Flujo:
    1. Normalizar datos (strip, lower)
    2. Validar campos obligatorios (email, username, first_name, last_name, password)
    3. Validar contraseña con validate_password
    4. Verificar unicidad de email y username
    5. Crear usuario con User.objects.create_user()
    6. Guardar bio y avatar (si existen)
    7. Guardar en cache positiva para login inmediato
    
    Uso: En el RegisterView.
    
    Nota: La operación es atómica (transaction.atomic) para garantizar integridad.
    """
    # 1. NORMALIZAR DATOS
    email = email.strip().lower() if email else ''
    username = username.strip() if username else ''
    first_name = first_name.strip() if first_name else ''
    last_name = last_name.strip() if last_name else ''
    bio = bio.strip() if bio else ''

    # 2. VALIDAR CAMPOS OBLIGATORIOS
    if not email:
        raise ValidationError("Email es requerido")

    if not username:
        raise ValidationError("El nombre de usuario es requerido")

    if not first_name:
        raise ValidationError("El nombre es requerido")

    if not last_name:
        raise ValidationError("El apellido es requerido")

    if not password:
        raise ValidationError("La contraseña es requerida")

    # 3. VALIDAR CONTRASEÑA
    validate_password(password)

    # 4. VERIFICAR UNICIDAD DE EMAIL Y USERNAME
    from .selectors import get_user_by_email, get_user_by_username
    
    # Verificar email
    try:
        existing_user = get_user_by_email(email=email, use_cache=True)
        if existing_user:
            raise ValidationError("El email ya está en uso")
    except ValidationError:
        # Si no existe, está bien
        pass
    except Exception:
        # Fallback: consulta directa
        if User.objects.filter(email=email).exists():
            raise ValidationError("El email ya está en uso")

    # Verificar username
    try:
        existing_user = get_user_by_username(username=username, use_cache=True)
        if existing_user:
            raise ValidationError("El nombre de usuario ya está en uso")
    except ValidationError:
        pass
    except Exception:
        if User.objects.filter(username=username).exists():
            raise ValidationError("El nombre de usuario ya está en uso")

    # 5. CREAR USUARIO
    user = User.objects.create_user(
        email=email,
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    # 6. GUARDAR CAMPOS OPCIONALES
    if bio:
        user.bio = bio

    if avatar:
        user.avatar = avatar

    user.save()

    # 7. GUARDAR EN CACHE POSITIVA
    _set_cached_user(user)

    return user


@transaction.atomic
def update_profile(
    *,
    user: User,
    first_name: str | None = None,
    last_name: str | None = None,
    bio: str | None = None,
    avatar: Any | None = None,
) -> User:
    """
    Actualiza el perfil de un usuario.
    
    Campos actualizables:
    - first_name: Nombre
    - last_name: Apellido
    - bio: Biografía
    - avatar: Foto de perfil
    
    Uso: En el UpdateProfileView.
    
    Nota: La operación es atómica (transaction.atomic) para garantizar integridad.
    """
    # Actualizar solo los campos que se proporcionaron
    if first_name is not None:
        user.first_name = first_name.strip()

    if last_name is not None:
        user.last_name = last_name.strip()
    
    if bio is not None:
        user.bio = bio.strip()

    if avatar is not None:
        user.avatar = avatar

    user.save()

    return user


@transaction.atomic
def change_password(
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    """
    Cambia la contraseña de un usuario.
    
    Validaciones:
    1. Contraseña actual es obligatoria
    2. Nueva contraseña es obligatoria
    3. La nueva contraseña no puede ser igual a la actual
    4. La contraseña actual debe ser correcta
    5. La nueva contraseña debe cumplir las políticas de seguridad
    
    Seguridad adicional:
    - Invalida todos los tokens activos del usuario (blacklist)
    
    Uso: En el ChangePasswordView.
    
    Nota: La operación es atómica (transaction.atomic) para garantizar integridad.
    """
    # 1. VALIDAR ENTRADA
    if not current_password:
        raise ValidationError("La contraseña actual es requerida")

    if not new_password:
        raise ValidationError("La contraseña nueva es requerida")
    
    if current_password == new_password:
        raise ValidationError("La contraseña nueva no puede ser igual a la actual")

    # 2. VERIFICAR CONTRASEÑA ACTUAL
    if not user.check_password(current_password):
        raise ValidationError("La contraseña actual es incorrecta")

    # 3. VALIDAR NUEVA CONTRASEÑA
    validate_password(new_password, user=user)

    # 4. ACTUALIZAR CONTRASEÑA
    user.set_password(new_password)
    user.save(update_fields=["password"])

    # 5. INVALIDAR TODOS LOS TOKENS ACTIVOS
    # Esto fuerza al usuario a volver a iniciar sesión
    OutstandingToken.objects.filter(user=user).delete()

    return user


# ============================================================
# SERVICIOS DE ESTADO DE CUENTA
# ============================================================

@transaction.atomic
def verify_user(*, user: User) -> User:
    """
    Marca un usuario como verificado (is_verified = True).
    
    Verificación significa que el usuario confirmó su email.
    
    Uso: En el VerifyAccountView (cuando el usuario confirma su email).
    
    Nota: La operación es atómica (transaction.atomic) para garantizar integridad.
    """
    if user.is_verified:
        raise ValidationError("El usuario ya se encuentra verificado")

    user.is_verified = True
    user.save(update_fields=["is_verified"])

    return user


@transaction.atomic
def deactivate_user(*, user: User) -> User:
    """
    Desactiva un usuario (is_active = False).
    
    Un usuario desactivado no puede iniciar sesión.
    
    Uso: En el DeactivateAccountView (cuando el usuario desactiva su cuenta).
    
    Nota: La operación es atómica (transaction.atomic) para garantizar integridad.
    """
    if not user.is_active:
        raise ValidationError("El usuario ya se encuentra desactivado")

    user.is_active = False
    user.save(update_fields=["is_active"])

    return user


@transaction.atomic
def activate_user(*, user: User) -> User:
    """
    Activa un usuario (is_active = True).
    
    Un usuario activo puede iniciar sesión.
    
    Uso: En el ActivateAccountView (cuando el usuario reactiva su cuenta).
    
    Nota: La operación es atómica (transaction.atomic) para garantizar integridad.
    """
    if user.is_active:
        raise ValidationError("El usuario ya se encuentra activo")

    user.is_active = True
    user.save(update_fields=["is_active"])

    return user
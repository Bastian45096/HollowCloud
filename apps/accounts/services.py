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

CACHE_NEGATIVE_TTL = 300  # 5 minutos
CACHE_NEGATIVE_PREFIX = "user_not_found"
MAX_ATTEMPTS_IP = 10
MAX_ATTEMPTS_EMAIL = 5
RATE_LIMIT_WINDOW = 300  # 5 minutos
TIMING_ATTACK_SLEEP = 0.1  # 100ms


# ============================================================
# FUNCIONES AUXILIARES DE CACHE (dentro de services.py)
# ============================================================

def _get_negative_cache_key(email: str) -> str:
    """Clave para cache negativa (usuario no existe)"""
    return f"{CACHE_NEGATIVE_PREFIX}:{email.lower()}"


def _is_user_blocked(email: str) -> bool:
    """Verificar si el email está bloqueado por cache negativa"""
    cache_key = _get_negative_cache_key(email)
    return cache.get(cache_key, False)


def _block_user(email: str) -> None:
    """Bloquear email en cache negativa (usuario no existe)"""
    cache_key = _get_negative_cache_key(email)
    cache.set(cache_key, True, CACHE_NEGATIVE_TTL)


def _unblock_user(email: str) -> None:
    """Desbloquear email de cache negativa"""
    cache_key = _get_negative_cache_key(email)
    cache.delete(cache_key)


def _get_rate_limit_key_ip(request) -> str:
    """Clave de rate limiting por IP"""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')
    ip = ip or 'unknown_ip'
    return f"login_attempts_ip:{ip}"


def _get_rate_limit_key_email(email: str) -> str:
    """Clave de rate limiting por email"""
    return f"login_attempts_email:{email.lower()}"


def _check_rate_limit(key: str, max_attempts: int, window: int = RATE_LIMIT_WINDOW) -> bool:
    """Verificar si se excedió el límite de intentos"""
    attempts = cache.get(key, 0)
    if attempts >= max_attempts:
        return False
    return True


def _increment_rate_limit(key: str, window: int = RATE_LIMIT_WINDOW) -> None:
    """Incrementar el contador de intentos"""
    attempts = cache.get(key, 0)
    cache.set(key, attempts + 1, window)


def _reset_rate_limit(key: str) -> None:
    """Resetear el contador de intentos"""
    cache.delete(key)


def _get_cached_user(email: str) -> Optional[User]:
    """Obtener usuario de cache positiva (1 hora)"""
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
    """Guardar usuario en cache positiva (1 hora)"""
    cache_key = f"user_authenticated:{user.email.lower()}"
    cache.set(cache_key, user.id, 3600)  # 1 hora


def _check_account_status(user: User) -> None:
    """Verificar el estado de la cuenta del usuario"""
    if not user.is_active:
        logger.warning(f"[Account] Cuenta inactiva: {user.email}")
        raise ValidationError("Tu cuenta ha sido desactivada. Contacta a soporte.")
    
    if not user.is_verified:
        logger.warning(f"[Account] Cuenta no verificada: {user.email}")
        raise ValidationError("Tu cuenta no está verificada. Revisa tu email.")


def generate_tokens(user: User) -> dict[str, str]:
    """
    Genera un par de tokens JWT para un usuario autenticado.
    """
    start = time.time()
    logger.info(f"[GenerateTokens] Iniciando generación de tokens para user_id={user.id}")
    
    # Tiempo 1: Crear refresh token
    t1 = time.time()
    refresh = RefreshToken.for_user(user)
    logger.info(f"[GenerateTokens] Refresh token creado en {(t1 - start)*1000:.2f}ms")
    
    # Tiempo 2: Obtener access token
    t2 = time.time()
    access = str(refresh.access_token)
    logger.info(f"[GenerateTokens] Access token generado en {(t2 - t1)*1000:.2f}ms")
    
    # Tiempo 3: Obtener refresh token como string
    t3 = time.time()
    refresh_str = str(refresh)
    logger.info(f"[GenerateTokens] Refresh token convertido en {(t3 - t2)*1000:.2f}ms")
    
    tokens = {
        "access": access,
        "refresh": refresh_str,
    }
    
    total = (time.time() - start) * 1000
    logger.info(f"[GenerateTokens] Tokens generados exitosamente en {total:.2f}ms total")
    
    return tokens

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
    Crear un nuevo usuario dentro de la plataforma.
    """
    logger.info(
        "[POST Crear Usuario] Solicitud recibida email=%s username=%s",
        email,
        username,
    )

    # Normalizamos los datos
    email = email.strip().lower()
    username = username.strip()
    first_name = first_name.strip() if first_name else ''
    last_name = last_name.strip() if last_name else ''

    logger.debug("[POST Crear Usuario] Datos normalizados correctamente")

    # Validaciones obligatorias
    if not email:
        logger.warning("[POST Crear Usuario] Validación fallida: el email es obligatorio")
        raise ValidationError("Email es requerido")

    if not username:
        logger.warning("[POST Crear Usuario] Validación fallida: el nombre de usuario es obligatorio")
        raise ValidationError("El nombre de usuario es requerido")

    # Verificar unicidad
    if User.objects.filter(email=email).exists():
        logger.warning("[POST Crear Usuario] El email ya se encuentra registrado email=%s", email)
        raise ValidationError("El email ya está en uso")

    if User.objects.filter(username=username).exists():
        logger.warning("[POST Crear Usuario] El nombre de usuario ya se encuentra registrado username=%s", username)
        raise ValidationError("El nombre de usuario ya está en uso")

    # Validar contraseña
    validate_password(password)

    try:
        logger.info("[POST Crear Usuario] Creando registro de usuario en la base de datos")

        # Crear usuario
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        if bio:
            user.bio = bio

      
        if avatar:
            logger.info(f"[POST Crear Usuario] Guardando avatar: {avatar.name}")
            user.avatar = avatar

        user.save()

        logger.info("[POST Crear Usuario] Usuario creado exitosamente user_id=%s", user.id)

        return user

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[POST Crear Usuario] Ocurrió un error inesperado durante la creación del usuario: %s", str(exc))
        logger.exception("[POST Crear Usuario] Detalle completo de la excepción")
        raise

def authenticate_user(*, email: str, password: str, request=None) -> User:
    """
    Autenticación con:
    - Cache negativa (bloquea emails inexistentes por 5 min)
    - Cache positiva (usuarios autenticados por 1 hora)
    - Rate limiting por IP y email
    - Protección timing attack
    - Mensajes genéricos
    """
    start = time.time()
    email = email.strip().lower()
    password = password.strip() if password else ''

    logger.info(f"[Authenticate] Inicio - email: {email}")

    # ============================================================
    # 1. VALIDACIÓN DE ENTRADA
    # ============================================================
    
    if not email or not password:
        logger.warning("[Authenticate] Credenciales vacías")
        raise ValidationError("Credenciales inválidas")

    logger.info(f"[Authenticate] Paso 1 - Validación entrada: {(time.time() - start)*1000:.2f}ms")

    # ============================================================
    # 2. CACHE NEGATIVA - ¿Email bloqueado?
    # ============================================================
    
    if _is_user_blocked(email):
        logger.warning(f"[Authenticate] Email bloqueado por cache negativa: {email}")
        raise ValidationError("Credenciales inválidas")

    logger.info(f"[Authenticate] Paso 2 - Cache negativa: {(time.time() - start)*1000:.2f}ms")

    # ============================================================
    # 3. RATE LIMITING
    # ============================================================
    
    client_ip = "0.0.0.0"
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            client_ip = x_forwarded.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR', '0.0.0.0')

    ip_key = _get_rate_limit_key_ip(request) if request else None
    email_key = _get_rate_limit_key_email(email)

    if ip_key and not _check_rate_limit(ip_key, MAX_ATTEMPTS_IP):
        logger.warning(f"[Authenticate] IP bloqueada: {client_ip}")
        raise ValidationError("Demasiados intentos. Espera 5 minutos.")

    if not _check_rate_limit(email_key, MAX_ATTEMPTS_EMAIL):
        logger.warning(f"[Authenticate] Email bloqueado por intentos: {email}")
        raise ValidationError("Demasiados intentos. Espera 5 minutos.")

    logger.info(f"[Authenticate] Paso 3 - Rate limiting: {(time.time() - start)*1000:.2f}ms")

    # ============================================================
    # 4. CACHE POSITIVA - ¿Usuario ya autenticado?
    # ============================================================
    
    cached_user = _get_cached_user(email)
    if cached_user and cached_user.check_password(password):
        logger.info(f"[Authenticate] Usuario recuperado de cache: {email}")
        logger.info(f"[Authenticate] Tiempo total: {(time.time() - start)*1000:.2f}ms")
        return cached_user

    logger.info(f"[Authenticate] Paso 4 - Cache positiva: {(time.time() - start)*1000:.2f}ms")

    # ============================================================
    # 5. TIMING ATTACK PROTECTION
    # ============================================================
    
    auth_start = time.time()

    try:
        # ============================================================
        # 6. AUTENTICACIÓN
        # ============================================================
        
        logger.info(f"[Authenticate] Paso 5 - Iniciando authenticate()")
        
        user = authenticate(username=email, password=password)
        
        logger.info(f"[Authenticate] Paso 5 - authenticate() completado en {(time.time() - auth_start)*1000:.2f}ms")

        if user is not None:
            # ============================================================
            # 7. LOGIN EXITOSO
            # ============================================================
            
            # Verificar cuenta activa
            if not user.is_active:
                logger.warning(f"[Authenticate] Cuenta inactiva: {user.email}")
                raise ValidationError("Credenciales inválidas")
            
            # Resetear rate limits
            if ip_key:
                _reset_rate_limit(ip_key)
            _reset_rate_limit(email_key)
            
            # Guardar en cache positiva
            _set_cached_user(user)
            
            # Desbloquear de cache negativa
            _unblock_user(email)
            
            total_time = (time.time() - start) * 1000
            logger.info(f"[Authenticate] Login exitoso - User: {user.email} - Tiempo total: {total_time:.2f}ms")
            return user

        # ============================================================
        # 8. LOGIN FALLIDO
        # ============================================================
        
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
        
        if not user_exists:
            _block_user(email)
            logger.warning(f"[Authenticate] Email no existe, bloqueado: {email}")
        else:
            logger.warning(f"[Authenticate] Contraseña incorrecta: {email}")

        # ============================================================
        # 9. TIMING ATTACK MITIGATION
        # ============================================================
        
        elapsed = time.time() - auth_start
        if elapsed < TIMING_ATTACK_SLEEP:
            logger.info(f"[Authenticate] Sleep por timing attack: {(TIMING_ATTACK_SLEEP - elapsed)*1000:.2f}ms")
            time.sleep(TIMING_ATTACK_SLEEP - elapsed)
        
        total_time = (time.time() - start) * 1000
        logger.info(f"[Authenticate] Login fallido - Tiempo total: {total_time:.2f}ms")
        raise ValidationError("Credenciales inválidas")

    except ValidationError:
        raise
    except Exception as exc:
        logger.error(f"[Authenticate] Error inesperado: {str(exc)}", exc_info=True)
        raise ValidationError("Error al autenticar. Intenta nuevamente.")

def login_user(*, email: str, password: str, request=None) -> Dict[str, Any]:
    """
    Iniciar sesión de un usuario con cache negativa y positiva.
    """
    email = email.strip().lower() if email else ''
    password = password.strip() if password else ''

    logger.info("[POST Login Usuario] Solicitud recibida, email=%s", email)

    # 1. VALIDACIÓN DE ENTRADA
    if not email or not password:
        logger.warning("[POST Login Usuario] Credenciales vacías")
        raise ValidationError("Email y contraseña son requeridos")

    # 2. CACHE NEGATIVA - ¿Usuario bloqueado?
    if _is_user_blocked(email):  
        logger.warning(f"[POST Login Usuario] Email bloqueado: {email}")
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
        logger.info(f"[POST Login Usuario] Usuario recuperado de cache: {email}")
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
            if ip_key:
                _reset_rate_limit(ip_key)  
            _reset_rate_limit(email_key)  

            _set_cached_user(user) 
            _unblock_user(email)  

            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            tokens = generate_tokens(user=user)

            logger.info("[POST Login Usuario] Login exitoso user_id=%s", user.id)

            return {
                "user": user,
                "tokens": tokens,
            }

        # 8. LOGIN FALLIDO
        if ip_key:
            _increment_rate_limit(ip_key) 
        _increment_rate_limit(email_key) 

        # Verificar si el usuario existe
        try:
            from .selectors import get_user_by_email
            user_exists = get_user_by_email(email=email, use_cache=False)
        except:
            user_exists = None

        if not user_exists:
            _block_user(email) 
            logger.warning(f"[POST Login Usuario] Email no existe, bloqueado: {email}")
        else:
            logger.warning(f"[POST Login Usuario] Contraseña incorrecta: {email}")

        # 9. TIMING ATTACK MITIGATION
        elapsed = time.time() - start_time
        if elapsed < TIMING_ATTACK_SLEEP:
            time.sleep(TIMING_ATTACK_SLEEP - elapsed)

        raise ValidationError("Credenciales inválidas")

    except ValidationError:
        raise
    except Exception as exc:
        logger.error("[POST Login Usuario] Error inesperado: %s", str(exc), exc_info=True)
        raise ValidationError("Error al iniciar sesión. Intenta nuevamente.")





def refresh_access_token(*, refresh_token: str) -> dict[str, str]:
    """
    Generar un nuevo access token a partir de un refresh token válido.

    Responsabilidades:
    - Validar que exista un refresh token.
    - Verificar que el token sea válido.
    - Generar un nuevo access token.
    - Mantener trazabilidad mediante logs.
    """

    logger.info(
        "[POST Renovar Token] Solicitud de renovación de token recibida"
    )

    if not refresh_token:

        logger.warning(
            "[POST Renovar Token] Validación fallida: refresh token requerido"
        )

        raise ValidationError(
            "Refresh token es requerido",
        )

    try:

        logger.debug(
            "[POST Renovar Token] Cargando refresh token"
        )

        refresh = RefreshToken(refresh_token)

        logger.debug(
            "[POST Renovar Token] Generando nuevo access token"
        )

        access_token = str(
            refresh.access_token
        )

        logger.info(
            "[POST Renovar Token] Access token renovado correctamente"
        )

        return {
            "access": access_token,
        }

    except TokenError:

        logger.warning(
            "[POST Renovar Token] El refresh token es inválido o expiró"
        )

        raise ValidationError(
            "Refresh token inválido o expirado",
        )

    except Exception as exc:

        logger.error(
            "[POST Renovar Token] Error inesperado durante la renovación del token: %s",
            str(exc),
        )

        logger.exception(
            "[POST Renovar Token] Detalle completo de la excepción"
        )

        raise


def logout_user(*, refresh_token: str) -> None:
    """
    Cerrar sesion de un usu
    
    Responsabilidades:
        - Invalidar el refresh token para que no pueda ser utilizado nuevamente.
        - Registrar trazabilidad del proceso
        - Evitar reutilización de token

    """

    logger.info(
        "[POST Cerrar Sesion] Solicitud de cierre de sesion recibida"
    )

    if not refresh_token:
        logger.warning(
            "[POST Cerrar Sesion] Validación fallida: el refresh token es obligatorio"
        )

    try:
        logger.debug(
            "[POST Cerrar Sesion] Cargando refresh token"
        )

        token = RefreshToken(refresh_token)

        logger.debug(
            "[POST Cerrar Sesion] Invalidando refresh token"
        )
        token.blacklist()

        logger.info(
            "[POST Cerrar Sesion] Sesion cerrada correctamente"
        )

    except TokenError:
        logger.warning("[POST Cerrar Sesion] Refresh token inválido o expirado")

        raise ValidationError("Token inválido o expirado")

    except Exception as exc:

        logger.error(
            "[POST Cerrar Sesion] Error inesperado durante el cierre de sesion: %s",
            str(exc),
        )

        logger.exception(
            "[POST Cerrar Sesion] Detalle completo de la excepción"
        )

        raise

@transaction.atomic
def update_profile(*, user: User,first_name: str | None = None,
                   last_name: str | None = None,
                   bio: str | None = None,
                   avatar: Any | None = None,
                   ) -> User:
    

    """
    Actualizar el perfil de un usuario.

    Responsabilidades:
     -Actualizar campos de perfil como nombre, apellido, biografía y avatar.
     -Mantener la trazabilidad mediante logs
     -Ejecutar la operación de forma atómica para garantizar la integridad de los datos.
    """

    logger.info(
        "[PATCH Actualizar Perfil] Solicitud de actualización de perfil recibida user_id=%s",
        user.id,
    )

    try:

        if first_name is not None:
            
            logger.debug("[PATCH Actualizar Perfil] Actualizando first_name")
            user.first_name = first_name.strip()

        if last_name is not None:

            logger.debug("[PATCH Actualizar Perfil] Actualizando last_name")
            user.last_name = last_name.strip()
        
        if bio is not None:
            logger.debug("[PATCH Actualizar Perfil] Actualizando bio")
            user.bio = bio.strip()

        if avatar is not None:
            logger.debug("[PATCH Actualizar Perfil] Actualizando avatar")
            user.avatar = avatar

        user.save()

        logger.info(
            "[PATCH Actualizar Perfil] Perfil actualizado exitosamente user_id=%s",
            user.id,
        )

        return user

    except Exception as exc:

        logger.error(
            "[PATCH Actualizar Perfil] Error inesperado durante la actualización del perfil: %s",
            str(exc),
        )

        logger.exception(
            "[PATCH Actualizar Perfil] Detalle completo de la excepción"
        )

        raise

@transaction.atomic
def change_password(*, user: User, current_password: str, new_password: str,) -> User:

    """
    Cambiar la contraseña de un usuario.

    Responsabilidades:
     - Validar contraseña actual.
     - Validar nueva contraseña según las políticas de seguridad.
     - Impedir reutilización de la contraseña actual.
     - Actualizar la contraseña de forma segura.
     - Mantener trazabilidad mediante logs.

    """

    logger.info(
        "[PATCH Cambiar Contraseña] Solicitud de cambio de contraseña recibida user_id=%s"
        , user.id,
    )

    if not current_password:

        logger.warning(
            "[PATCH Cambiar Contraseña] Validación fallida: la contraseña actual es obligatoria"
        )

        raise ValidationError(
            "La contraseña actual es requerida",
        )

    if not new_password:

        logger.warning(
            "[PATCH Cambiar Contraseña] Validación fallida: la contraseña nueva es obligatoria"
        )

        raise ValidationError(
            "La contraseña nueva es requerida",
        )
    
    if current_password == new_password:

        logger.warning(
            "[PATCH Cambiar Contraseña] Validación fallida: la contraseña nueva no puede ser igual a la actual"
        )

        raise ValidationError(
            "La contraseña nueva no puede ser igual a la actual",
        )

    try:

        logger.debug("[PATCH Cambiar Contraseña] Verificando contraseña actual")

        if not user.check_password(current_password):

            logger.warning(
                "[PATCH Cambiar Contraseña] La contraseña actual es incorrecta user_id=%s",
                user.id,
            )

            raise ValidationError(
                "La contraseña actual es incorrecta",
            )

        logger.debug("[PATCH Cambiar Contraseña] Actualizando contraseña")

        validate_password(
            new_password,
            user=user,
        )

        logger.debug("[PATCH Cambiar Contraseña] Nueva contraseña validada correctamente")

        user.set_password(new_password)
        user.save(
            update_fields=["password"],
        )


        logger.debug(
            "[PATCH Cambiar Contraseña] Invalidando sesiones activas user_id=%s",
            user.id,
        )

        OutstandingToken.objects.filter(
            user=user,
        ).delete()

        logger.info(
            "[PATCH Cambiar Contraseña] Sesiones activas invalidadas correctamente user_id=%s",
            user.id,)

        logger.info(
            "[PATCH Cambiar Contraseña] Contraseña actualizada exitosamente"
        )

        return user

    except ValidationError:
        raise

    except Exception as exc:

        logger.error(
            "[PATCH Cambiar Contraseña] Error inesperado durante el cambio de contraseña: %s",
            str(exc),
        )

        logger.exception(
            "[PATCH Cambiar Contraseña] Detalle completo de la excepción"
        )

        raise

@transaction.atomic
def verify_user(*, user: User) ->User:

    """
    Marcar un usuario como verificado

    Responsabilidades

     - Validar que el usuario exista.
     - Evitar verificaciones duplicadas.
     - Actualizar estado de verificacion.
     - Mantener la trazabilidad mediante logs.
    """

    logger.info(
        "[PATCH Verificar Usuario] Solicitud recibida user_id=%s",
        user.id,
    )

    if user.is_verified:

        logger.warning(
            "[PATCH Verificar Usuario] Validación fallida: el usuario ya se encuentra verificado user_id=%s",
            user.id,
        )

        raise ValidationError(
            "El usuario ya se encuentra verificado",
        )

    try:

        logger.debug(
            "[PATCH Verificar Usuario] Actualizando estado de verificación"
        )

        user.is_verified = True

        user.save(
            update_fields=["is_verified"],
        )

        logger.info(
            "[PATCH Verificar Usuario] Usuario verificado exitosamente user_id=%s",
            user.id,
        )

        return user
    
    except ValidationError:
        raise

    except Exception as exc:

        logger.error(
            "[PATCH Verificar Usuario] Error inesperado durante la verificación del usuario: %s",
            str(exc),
        )

        logger.exception(
            "[PATCH Verificar Usuario] Detalle completo de la excepción"
        )

        raise

@transaction.atomic
def deactivate_user(*, user: User) -> User:
    """
    Desactivar un usuario.

    Responsabilidades:
     - Validar que el usuario exista.
     - Evitar desactivaciones duplicadas.
     - Actualizar estado de activación.
     - Mantener la trazabilidad mediante logs.
    """

    logger.info(
        "[PATCH Desactivar Usuario] Solicitud recibida user_id=%s",
        user.id,
    )

    if not user.is_active:

        logger.warning(
            "[PATCH Desactivar Usuario] Validación fallida: el usuario ya se encuentra desactivado user_id=%s",
            user.id,
        )

        raise ValidationError(
            "El usuario ya se encuentra desactivado",
        )

    try:

        logger.debug(
            "[PATCH Desactivar Usuario] Actualizando estado de activación"
        )

        user.is_active = False

        user.save(
            update_fields=["is_active"],
        )

        logger.info(
            "[PATCH Desactivar Usuario] Usuario desactivado exitosamente user_id=%s",
            user.id,
        )

        return user
    
    except ValidationError:
        raise

    except Exception as exc:

        logger.error(
            "[PATCH Desactivar Usuario] Error inesperado durante la desactivación del usuario: %s",
            str(exc),
        )

        logger.exception(
            "[PATCH Desactivar Usuario] Detalle completo de la excepción"
        )

        raise

@transaction.atomic
def activate_user(*, user: User) -> User:
    """
    Activar un usuario.

    Responsabilidades:
     - Validar que el usuario exista.
     - Evitar activaciones duplicadas.
     - Actualizar estado de activación.
     - Mantener la trazabilidad mediante logs.
    """

    logger.info(
        "[PATCH Activar Usuario] Solicitud recibida user_id=%s",
        user.id,
    )

    if user.is_active:

        logger.warning(
            "[PATCH Activar Usuario] Validación fallida: el usuario ya se encuentra activo user_id=%s",
            user.id,
        )

        raise ValidationError(
            "El usuario ya se encuentra activo",
        )

    try:

        logger.debug(
            "[PATCH Activar Usuario] Actualizando estado de activación"
        )

        user.is_active = True

        user.save(
            update_fields=["is_active"],
        )

        logger.info(
            "[PATCH Activar Usuario] Usuario activado exitosamente user_id=%s",
            user.id,
        )

        return user
    
    except ValidationError:
        raise

    except Exception as exc:

        logger.error(
            "[PATCH Activar Usuario] Error inesperado durante la activación del usuario: %s",
            str(exc),
        )

        logger.exception(
            "[PATCH Activar Usuario] Detalle completo de la excepción"
        )

        raise



from __future__ import annotations
import logging
from re import I
from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from apps.accounts.models import User

logger = logging.getLogger(__name__)


def generate_tokens(user: User) -> dict[str, str]:
    """
    Genera un par de tokens JWT para un usuario autenticado.

    Retorna:
    - access token: utilizado para acceder a los recursos protegidos.
    - refresh token: utilizado para solicitar nuevos access tokens
      sin necesidad de volver a iniciar sesión.
    """

    logger.info(
        "[POST Generar Tokens] Iniciando generación de tokens para user_id=%s",
        user.id,
    )

    # SimpleJWT utiliza el refresh token como token principal.
    # A partir de este objeto también se genera automáticamente
    # el access token asociado al usuario.
    refresh = RefreshToken.for_user(user)

    logger.debug(
        "[POST Generar Tokens] Refresh token generado correctamente para user_id=%s",
        user.id,
    )

    # Se retornan ambos tokens porque el cliente necesitará:
    # - access: para autenticarse en las solicitudes.
    # - refresh: para renovar la sesión cuando el access expire.
    tokens = {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }

    logger.info(
        "[POST Generar Tokens] Tokens generados exitosamente para user_id=%s",
        user.id,
    )

    return tokens

@transaction.atomic
def create_user(*, email: str, username: str, password: str, first_name: str, last_name: str,) -> User:
    """
    Crear un nuevo usuario dentro de la plataforma.

    Responsabilidades:
    - Normalizar datos de entrada.
    - Validar campos obligatorios.
    - Garantizar unicidad de email y username.
    - Validar contraseña según las reglas configuradas en Django.
    - Crear el usuario de forma atómica.
    """

    logger.info(
        "[POST Crear Usuario] Solicitud recibida email=%s username=%s",
        email,
        username,
    )

    # Normalizamos los datos para evitar diferencias por espacios
    # o mayúsculas/minúsculas que puedan generar duplicados.
    email = email.strip().lower()
    username = username.strip()
    first_name = first_name.strip()
    last_name = last_name.strip()

    logger.debug(
        "[POST Crear Usuario] Datos normalizados correctamente"
    )

    # Validamos primero los datos obligatorios.
    # Es preferible fallar temprano antes de realizar consultas a la base de datos.
    if not email:
        logger.warning(
            "[POST Crear Usuario] Validación fallida: el email es obligatorio"
        )
        raise ValidationError(
            "Email es requerido",
        )

    if not username:
        logger.warning(
            "[POST Crear Usuario] Validación fallida: el nombre de usuario es obligatorio"
        )
        raise ValidationError(
            "El nombre de usuario es requerido",
        )

    if not first_name:
        logger.warning(
            "[POST Crear Usuario] Validación fallida: el nombre es obligatorio"
        )
        raise ValidationError(
            "First name es requerido",
        )

    if not last_name:
        logger.warning(
            "[POST Crear Usuario] Validación fallida: el apellido es obligatorio"
        )
        raise ValidationError(
            "Last name es requerido",
        )

    logger.debug(
        "[POST Crear Usuario] Verificando disponibilidad del email"
    )

    # El email debe ser único dentro de la plataforma.
    # La validación temprana nos permite entregar un error de negocio entendible.
    if User.objects.filter(email=email).exists():
        logger.warning(
            "[POST Crear Usuario] El email ya se encuentra registrado email=%s",
            email,
        )
        raise ValidationError(
            "El email ya está en uso",
        )

    logger.debug(
        "[POST Crear Usuario] Verificando disponibilidad del nombre de usuario"
    )

    # El username también debe ser único.
    # Esto evita conflictos de identidad dentro de la aplicación.
    if User.objects.filter(username=username).exists():
        logger.warning(
            "[POST Crear Usuario] El nombre de usuario ya se encuentra registrado username=%s",
            username,
        )
        raise ValidationError(
            "El nombre de usuario ya está en uso",
        )

    logger.debug(
        "[POST Crear Usuario] Validando contraseña"
    )

    # Delegamos la validación al sistema de validadores de Django
    # para mantener una única fuente de verdad sobre las políticas de seguridad.
    validate_password(password)

    try:

        logger.info(
            "[POST Crear Usuario] Creando registro de usuario en la base de datos"
        )

        # Toda la operación se encuentra protegida por una transacción.
        # Si ocurre cualquier error, ningún cambio será persistido.
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        logger.info(
            "[POST Crear Usuario] Usuario creado exitosamente user_id=%s",
            user.id,
        )

        return user

    except ValidationError:
        raise

    except Exception as exc:

        # Capturamos errores inesperados para dejar trazabilidad
        # completa en los logs antes de propagar la excepción.
        logger.error(
            "[POST Crear Usuario] Ocurrió un error inesperado durante la creación del usuario: %s",
            str(exc),
        )

        logger.exception(
            "[POST Crear Usuario] Detalle completo de la excepción"
        )

        raise

def authenticate_user(*, email: str, password: str,) -> User:
    """
    Autenticar un usuario utilizando email y contraseña.

    Responsabilidades:
    - Normalizar email.
    - Validar campos obligatorios.
    - Verificar credenciales.
    - Verificar que la cuenta esté activa.
    - Retornar la instancia autenticada.
    """

    logger.info(
        "[POST Iniciar Sesión] Solicitud de autenticación recibida email=%s",
        email,
    )

    # Normalizamos el email para evitar diferencias por
    # mayúsculas, minúsculas o espacios accidentales.
    email = email.strip().lower()

    logger.debug(
        "[POST Iniciar Sesión] Email normalizado correctamente"
    )

    # Validamos datos obligatorios antes de consultar la base de datos.
    if not email:

        logger.warning(
            "[POST Iniciar Sesión] Validación fallida: el email es obligatorio"
        )

        raise ValidationError(
            "Email es requerido",
        )

    if not password:

        logger.warning(
            "[POST Iniciar Sesión] Validación fallida: la contraseña es obligatoria"
        )

        raise ValidationError(
            "La contraseña es requerida",
        )

    try:

        logger.debug(
            "[POST Iniciar Sesión] Verificando credenciales del usuario"
        )

        # Django utiliza USERNAME_FIELD internamente.
        # Como User.USERNAME_FIELD = "email",
        # authenticate utilizará el email para autenticar.
        user = authenticate(
            username=email,
            password=password,
        )

        if user is None:

            logger.warning(
                "[POST Iniciar Sesión] Credenciales inválidas email=%s",
                email,
            )

            raise ValidationError(
                "Credenciales inválidas",
            )

        # Verificación adicional de seguridad.
        if not user.is_active:

            logger.warning(
                "[POST Iniciar Sesión] Usuario deshabilitado user_id=%s",
                user.id,
            )

            raise ValidationError(
                "La cuenta se encuentra deshabilitada",
            )

        logger.info(
            "[POST Iniciar Sesión] Usuario autenticado correctamente user_id=%s",
            user.id,
        )

        return user

    except ValidationError:
        raise

    except Exception as exc:

        logger.error(
            "[POST Iniciar Sesión] Error inesperado durante la autenticación: %s",
            str(exc),
        )

        logger.exception(
            "[POST Iniciar Sesión] Detalle completo de la excepción"
        )

        raise

def login_user(*, email: str, password: str,) -> dict[str, Any]:

    """
    Iniciar sesión de un usuario.

    Responsabilidades:
    - Actualizar fecha de ultimo acceso
    - Autenticar al usuario.
    - Generar tokens JWT
    - Retornar usuario y tokens
    """



    logger.info(
        "[POST Login Usuario] Solicitud de inicio de sesion recibida, email=%s",
        email,
    )

    try:

        logger.debug(
            "[POST Login Usuario] Iniciando proceso de autenticacion"
        )

        user = authenticate_user(email=email, password=password)

        logger.debug(
            "[POST Login Usuario] Actualizando fecha de ultimo acceso"
        )

        user.last_login = timezone.now()
        user.save(
            update_fields=["last_login"],
        )

        logger.debug(
            "[POST Login Usuario] Generando tokens JWT"
        )

        tokens = generate_tokens(user,)

        logger.info("[POST Login Usuario] Inicio de sesion exitoso user_id=%s",
        user.id,)

        return{
            "user": user,
            "tokens": tokens,
        }
    
    except ValidationError:
        raise

        
    
    except Exception as exc:
        logger.error(
            "[POST Login Usuario] Error inesperado durante el inicio de sesion: %s",
            str(exc),
        )
        logger.exception(
            "[POST Login Usuario] Detalle completo de la excepción"
        )
        raise


from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


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
def get_user_by_id(*, user_id: int) -> User:
    """
    Obtener un usuario por su ID.
    """

    logger.info(
        "[GET Usuario] Buscando usuario user_id=%s",
        user_id,
    )

    if not user_id:

        logger.warning("[GET Usuario] es obligatorio")

        raise ValidationError(
            "User ID es requerido",
        )
    
    try:

        user = User.objects.filter(
            id=user_id,
        ).first()

        if user is None:
            
            logger.warning("[GET Usuario] Usuario no encontrado user_id=%s",
            user_id,)

            raise ValidationError("Usuario no encontrado")

        logger.info(
            "[GET Usuario] Usuario encontrado exitosamente user_id=%s",
            user_id,
        )

        return user

    except ValidationError:
        raise

    except Exception as exc:
        
        logger.error(
            "[GET Usuario] Error inesperado: %s",
            str(exc),
        )

        logger.exception(
            "[GET Usuario] Detalle completo de la excepción"
        )

        raise

@transaction.atomic
def get_user_by_email(*, email: str)-> User:
    """
    Obtener un usuario a partir de su correo electronico
    
    Responsabilidades:
        - Normalizar el email de entrada.
        - Validar que el email exista.
        - Buscar el usuario
        - Retornar la instancia encontrada
    """

    logger.info("[GET Usuario] Buscando usuario por email=%s",
                email,)

    email = email.strip().lower()

    logger.debug("[DEBUG Usuario] Email normalizado correctamente")

    if not email:

        logger.warning("[GET Usuario] Validación fallida: el email es obligatorio")

        raise ValidationError(
            "Email es requerido",
        )
    
    try:

        logger.debug(
            "[GET Usuario] Buscando usuario en la base de datos"
        )

        user = User.objects.filter(
            email=email,

        ).first()

        if user is None:

            logger.warning(
                "[GET Usuario] Usuario no encontrado email=%s",
                email,
            )

            raise ValidationError(
                "Usuario no encontrado",
            )

        logger.info(
            "[GET Usuario] Usuario encontrado exitosamente user_id=%s",
            user.id,
        )

        return user
    
    except ValidationError:
        raise

    except Exception as exc:

        logger.error(
            "[GET Usuario] Error inesperado: %s",
            str(exc),
        )

        logger.exception(
            "[GET Usuario] Detalle completo de la excepción"
        )

        raise

def get_user_by_username(*, username: str) -> User:

    """
    Obtener un usuario a partir de su nombre de usuario.

    Responsabilidades:
        - Normalizar el username de entrada.
        - Validar que el username exista.
        - Buscar el usuario
        - Retornar la instancia encontrada
    """

    logger.info("[GET Usuario] Buscando usuario por username=%s",
                username,)

    username = username.strip().lower()

    logger.debug("[DEBUG Usuario] Username normalizado correctamente")

    if not username:

        logger.warning("[GET Usuario] Validación fallida: el username es obligatorio")

        raise ValidationError(
            "Username es requerido",
        )

    try:

        logger.debug(
            "[GET Usuario] Buscando usuario en la base de datos"
        )

        user = User.objects.filter(
            username=username,
        ).first()

        if user is None:

            logger.warning(
                "[GET Usuario] Usuario no encontrado username=%s",
                username,
            )

            raise ValidationError(
                "Usuario no encontrado",
            )

        logger.info(
            "[GET Usuario] Usuario encontrado exitosamente user_id=%s",
            user.id,
        )

        return user

    except ValidationError:
        raise

    except Exception as exc:

        logger.error(
            "[GET Usuario] Error inesperado: %s",
            str(exc),
        )

        logger.exception(
            "[GET Usuario] Detalle completo de la excepción"
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



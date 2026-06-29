# apps/accounts/endpoints.py

"""
Endpoints de la aplicación accounts.
Maneja registro, login, perfil, cambio de contraseña, verificación y activación/desactivación de cuentas.

Cada endpoint incluye logs detallados para trazabilidad completa:
- INICIO: Marca el comienzo de la petición
- PROCESO: Cada fase intermedia (validación, BD, tokens, etc.)
- SUCCESS: Confirmación de que una fase se completó
- ERROR: Captura de excepciones con contexto
- FIN EXITOSO: Marca el final exitoso de la petición
- IP Cliente: Para auditoría de seguridad
- Email/ID Usuario: Para trazabilidad de quién hizo qué
"""

from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.permissions import IsAccountActive, IsVerified
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UpdateProfileSerializer,
    UserSerializer,
)
from apps.accounts.services import(
    authenticate_user,
    change_password,
    create_user,
    generate_tokens,
    logout_user,
    update_profile,
    verify_user,
    deactivate_user,
    activate_user,
)
from apps.accounts.selectors import get_user_by_id

import logging

# Configuración del logger para este archivo
# El nombre del logger será 'apps.accounts.endpoints'
logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    Endpoint para registro de nuevos usuarios.
    Permite a cualquier usuario (sin autenticar) crear una cuenta.
    
    Flujo:
    1. Validar datos con RegisterSerializer
    2. Crear usuario en base de datos
    3. Generar tokens JWT (access + refresh)
    4. Retornar usuario + tokens
    """
    permission_classes = [AllowAny]  # Cualquier persona puede registrarse

    def post(self, request):
        """
        Maneja la solicitud POST para registrar un nuevo usuario.
        """
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [RegisterView] - Solicitud POST de registro")
        logger.info(f"IP Cliente: {self._get_client_ip(request)}")
        logger.info(f"Email solicitado: {request.data.get('email', 'NO_PROVIDED')}")
        logger.info("=" * 60)
        
        # Variable para rastrear en qué fase falló si ocurre un error
        fase_actual = "INICIO"

        try:
            # ============================================================
            # FASE 1: VALIDACION DE DATOS
            # ============================================================
            fase_actual = "Validacion de datos"
            logger.info(f"PROCESO [RegisterView] - Fase: {fase_actual}")
            logger.info("PROCESO [RegisterView] - Validando datos de entrada con RegisterSerializer")
            
            # El serializer valida email único, contraseña, etc.
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)  # Si falla, lanza ValidationError
            
            # Log de éxito en validación
            logger.info(f"SUCCESS [RegisterView] - Datos validados correctamente para: {serializer.validated_data.get('email')}")

            # ============================================================
            # FASE 2: CREACION DE USUARIO EN BASE DE DATOS
            # ============================================================
            fase_actual = "Creacion de usuario en BD"
            logger.info(f"PROCESO [RegisterView] - Fase: {fase_actual}")
            logger.info("PROCESO [RegisterView] - Creando usuario en base de datos")
            
            # El método save() del serializer crea el usuario
            # Esto ejecuta la lógica de create_user en el serializer
            user = serializer.save()
            
            # Log de éxito en creación
            logger.info(f"SUCCESS [RegisterView] - Usuario creado en BD: {user.email} (ID: {user.id})")

            # ============================================================
            # FASE 3: GENERACION DE TOKENS JWT
            # ============================================================
            fase_actual = "Generacion de tokens JWT"
            logger.info(f"PROCESO [RegisterView] - Fase: {fase_actual}")
            logger.info("PROCESO [RegisterView] - Generando tokens de acceso y refresco")
            
            # Genera access token y refresh token para el usuario
            tokens = generate_tokens(user=user)
            
            # Log de éxito en generación de tokens
            logger.info(f"SUCCESS [RegisterView] - Tokens generados para: {user.email}")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [RegisterView] - Usuario registrado: {user.email} (ID: {user.id})")
            logger.info("=" * 60)
            
            # Retorna el usuario creado + sus tokens
            return Response(
                {
                    "message": "Usuario registrado exitosamente",
                    "user": UserSerializer(user, context={'request': request}).data,
                    "tokens": tokens,
                },
                status=status.HTTP_201_CREATED,  # 201 Created
            )

        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [RegisterView] - Fase fallida: {fase_actual}")
            logger.error(f"ERROR [RegisterView] - Motivo: {str(e)}")
            logger.error(f"ERROR [RegisterView] - Email: {request.data.get('email', 'NO_PROVIDED')}")
            logger.error("=" * 60)
            # exc_info=True incluye el stack trace completo en el log
            logger.error("ERROR [RegisterView] - Stack trace:", exc_info=True)
            raise e  # Re-lanza la excepción para que DRF la maneje

    def _get_client_ip(self, request):
        """
        Obtiene la IP real del cliente.
        Maneja proxies (X-Forwarded-For) para obtener la IP original.
        """
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            # Si hay múltiples IPs, la primera es la del cliente original
            return x_forwarded.split(',')[0]
        # Fallback: REMOTE_ADDR es la IP directa
        return request.META.get('REMOTE_ADDR')


class LoginView(APIView):
    """
    Endpoint para inicio de sesión.
    Autentica a un usuario y devuelve tokens JWT.
    
    Flujo:
    1. Validar credenciales con LoginSerializer
    2. Autenticar usuario (verificar email + password)
    3. Generar tokens JWT
    4. Actualizar last_login
    5. Retornar usuario + tokens
    """
    permission_classes = [AllowAny]  # Cualquier persona puede intentar login

    def post(self, request):
        """
        Maneja la solicitud POST para iniciar sesión.
        """
        # Obtener datos iniciales para el log
        client_ip = self._get_client_ip(request)
        email = request.data.get('email', 'NO_PROVIDED')
        
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [LoginView] - Solicitud POST de login")
        logger.info(f"IP Cliente: {client_ip}")
        logger.info(f"Email: {email}")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: VALIDACION DE CREDENCIALES
            # ============================================================
            logger.info("PROCESO [LoginView] - Fase: Validacion de credenciales")
            logger.info("PROCESO [LoginView] - Validando credenciales con LoginSerializer")
            
            # El LoginSerializer valida que email y password no estén vacíos
            serializer = LoginSerializer(data=request.data)
            if not serializer.is_valid():
                # Log de advertencia: credenciales inválidas (formato)
                logger.warning("=" * 60)
                logger.warning(f"WARNING [LoginView] - Validacion fallida para: {email}")
                logger.warning(f"WARNING [LoginView] - Errores: {serializer.errors}")
                logger.warning("=" * 60)
                return Response(
                    {"error": "Credenciales invalidas"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"SUCCESS [LoginView] - Credenciales validas para: {email}")

            # ============================================================
            # FASE 2: AUTENTICACION DE USUARIO
            # ============================================================
            logger.info("PROCESO [LoginView] - Fase: Autenticacion de usuario")
            logger.info("PROCESO [LoginView] - Verificando email y contraseña")
            
            # authenticate_user valida email + password y retorna el usuario
            # Si falla, lanza ValidationError
            user = authenticate_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                request=request  # Para pasar contexto de la petición
            )
            
            # Log de éxito en autenticación
            logger.info(f"SUCCESS [LoginView] - Usuario autenticado: {user.email} (ID: {user.id})")

            # ============================================================
            # FASE 3: GENERACION DE TOKENS
            # ============================================================
            logger.info("PROCESO [LoginView] - Fase: Generacion de tokens")
            logger.info("PROCESO [LoginView] - Generando tokens de acceso y refresco")
            
            tokens = generate_tokens(user)
            
            logger.info("SUCCESS [LoginView] - Tokens generados para: {user.email}")

            # ============================================================
            # FASE 4: ACTUALIZACION DE LAST_LOGIN
            # ============================================================
            logger.info("PROCESO [LoginView] - Fase: Actualizacion de last_login")
            logger.info("PROCESO [LoginView] - Actualizando timestamp de ultimo inicio de sesion")
            
            # Actualiza la fecha/hora del último login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            logger.info(f"SUCCESS [LoginView] - last_login actualizado para: {user.email}")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [LoginView] - Login exitoso: {user.email} (ID: {user.id})")
            logger.info(f"FIN EXITOSO [LoginView] - IP Cliente: {client_ip}")
            logger.info("=" * 60)
            
            # Retorna el usuario autenticado + sus tokens
            return Response({
                "message": "Inicio de sesion exitoso",
                "user": UserSerializer(user, context={'request': request}).data,
                "tokens": tokens,
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            # ============================================================
            # MANEJO DE ERROR DE AUTENTICACION (CREDENCIALES INVALIDAS)
            # ============================================================
            logger.warning("=" * 60)
            logger.warning(f"WARNING [LoginView] - Credenciales invalidas para: {email}")
            logger.warning(f"WARNING [LoginView] - Motivo: {str(e)}")
            logger.warning(f"WARNING [LoginView] - IP Cliente: {client_ip}")
            logger.warning("=" * 60)
            return Response(
                {"error": "Credenciales invalidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES INESPERADOS
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [LoginView] - Error inesperado para: {email}")
            logger.error(f"ERROR [LoginView] - Motivo: {str(e)}")
            logger.error(f"ERROR [LoginView] - IP Cliente: {client_ip}")
            logger.error("=" * 60, exc_info=True)
            raise e

    def _get_client_ip(self, request):
        """
        Obtiene la IP real del cliente.
        Maneja proxies (X-Forwarded-For) para obtener la IP original.
        """
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class LogoutView(APIView):
    """
    Endpoint para cerrar sesión.
    Invalida el refresh token para que no pueda ser usado nuevamente.
    
    Requiere:
    - Usuario autenticado
    - Cuenta activa
    
    Flujo:
    1. Recibir refresh token del body
    2. Invalidarlo (blacklist)
    3. Retornar confirmación
    """
    permission_classes = [IsAuthenticated, IsAccountActive]  # Usuario autenticado y activo

    def post(self, request):
        """
        Maneja la solicitud POST para cerrar sesión.
        """
        # Obtener datos para el log
        client_ip = self._get_client_ip(request)
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [LogoutView] - Solicitud POST de logout")
        logger.info(f"IP Cliente: {client_ip}")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: OBTENER REFRESH TOKEN
            # ============================================================
            logger.info("PROCESO [LogoutView] - Fase: Obteniendo refresh token")
            
            # Obtener el refresh token del body de la petición
            refresh_token = request.data.get("refresh")
            
            if refresh_token:
                logger.info("PROCESO [LogoutView] - Refresh token recibido")

                # ============================================================
                # FASE 2: INVALIDAR REFRESH TOKEN
                # ============================================================
                logger.info("PROCESO [LogoutView] - Fase: Invalidando refresh token")
                logger.info("PROCESO [LogoutView] - Agregando refresh token a la blacklist")
                
                # logout_user invalida el refresh token (blacklist)
                logout_user(refresh_token=refresh_token)
                
                logger.info("SUCCESS [LogoutView] - Refresh token invalidado")
            else:
                # Si no se proporciona refresh token, solo logueamos la advertencia
                logger.warning("WARNING [LogoutView] - No se proporciono refresh token")
                logger.warning("WARNING [LogoutView] - El token no sera invalidado")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [LogoutView] - Logout exitoso: {user_email} (ID: {user_id})")
            logger.info(f"FIN EXITOSO [LogoutView] - IP Cliente: {client_ip}")
            logger.info("=" * 60)
            
            return Response({
                "message": "Cierre de sesion exitoso",
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [LogoutView] - Error en logout para: {user_email}")
            logger.error(f"ERROR [LogoutView] - Motivo: {str(e)}")
            logger.error(f"ERROR [LogoutView] - IP Cliente: {client_ip}")
            logger.error("=" * 60, exc_info=True)
            raise e

    def _get_client_ip(self, request):
        """
        Obtiene la IP real del cliente.
        Maneja proxies (X-Forwarded-For) para obtener la IP original.
        """
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class ProfileView(APIView):
    """
    Endpoint para obtener y actualizar el perfil del usuario autenticado.
    
    GET: Obtiene los datos del perfil (incluye avatar)
    PATCH: Actualiza datos del perfil (nombre, apellido, bio, avatar, etc.)
    
    Requiere:
    - Usuario autenticado
    - Cuenta activa
    """
    permission_classes = [IsAuthenticated, IsAccountActive]
    # Permite recibir archivos (avatar) en el PATCH
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        """
        Maneja la solicitud GET para obtener el perfil del usuario.
        """
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION GET
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [ProfileView] - Solicitud GET de perfil")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: SERIALIZAR DATOS DEL USUARIO
            # ============================================================
            logger.info("PROCESO [ProfileView] - Fase: Serializando datos del usuario")
            
            # Serializa el usuario para devolverlo como JSON
            # context={'request': request} es necesario para que las URLs de avatares sean absolutas
            serializer = UserSerializer(request.user, context={'request': request})
            
            logger.info("SUCCESS [ProfileView] - Datos del usuario serializados")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [ProfileView] - Perfil obtenido: {user_email}")
            logger.info("=" * 60)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [ProfileView] - Error al obtener perfil de: {user_email}")
            logger.error(f"ERROR [ProfileView] - Motivo: {str(e)}")
            logger.error("=" * 60, exc_info=True)
            raise e

    def patch(self, request):
        """
        Maneja la solicitud PATCH para actualizar el perfil del usuario.
        """
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION PATCH
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [ProfileView] - Solicitud PATCH de actualizacion de perfil")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        
        # Log de los datos recibidos (solo las claves, no los valores por seguridad)
        data_keys = list(request.data.keys()) if request.data else []
        file_keys = list(request.FILES.keys()) if request.FILES else []
        logger.info(f"Datos recibidos (campos): {data_keys}")
        logger.info(f"Archivos recibidos: {file_keys}")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: VALIDACION DE DATOS
            # ============================================================
            logger.info("PROCESO [ProfileView] - Fase: Validacion de datos")
            logger.info("PROCESO [ProfileView] - Validando datos con UserSerializer")
            
            # UserSerializer valida los datos del perfil
            # partial=True permite actualizar solo algunos campos
            serializer = UserSerializer(
                request.user,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            
            if not serializer.is_valid():
                # Log de advertencia: validación fallida
                logger.warning("=" * 60)
                logger.warning(f"WARNING [ProfileView] - Validacion fallida para: {user_email}")
                logger.warning(f"WARNING [ProfileView] - Errores: {serializer.errors}")
                logger.warning("=" * 60)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info("SUCCESS [ProfileView] - Datos validados correctamente")

            # ============================================================
            # FASE 2: GUARDAR CAMBIOS
            # ============================================================
            logger.info("PROCESO [ProfileView] - Fase: Guardando cambios en BD")
            logger.info("PROCESO [ProfileView] - Actualizando perfil del usuario")
            
            # El serializer guarda los cambios en la base de datos
            serializer.save()
            
            logger.info("SUCCESS [ProfileView] - Perfil actualizado en BD")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [ProfileView] - Perfil actualizado: {user_email}")
            logger.info("=" * 60)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [ProfileView] - Error al actualizar perfil de: {user_email}")
            logger.error(f"ERROR [ProfileView] - Motivo: {str(e)}")
            logger.error("=" * 60, exc_info=True)
            raise e


class UpdateProfileView(APIView):
    """
    Endpoint para actualización avanzada del perfil.
    Similar a ProfileView.patch pero con un serializer específico.
    
    Útil cuando se necesita validación adicional o lógica de negocio específica.
    
    Requiere:
    - Usuario autenticado
    - Cuenta activa
    """
    permission_classes = [IsAuthenticated, IsAccountActive]
    # CRÍTICO: Permite recibir archivos (avatar, documentos, etc.)
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        """
        Maneja la solicitud PATCH para actualización avanzada del perfil.
        """
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [UpdateProfileView] - Solicitud PATCH de actualizacion de perfil")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        
        data_keys = list(request.data.keys()) if request.data else []
        file_keys = list(request.FILES.keys()) if request.FILES else []
        logger.info(f"Datos recibidos (campos): {data_keys}")
        logger.info(f"Archivos recibidos: {file_keys}")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: VALIDACION DE DATOS
            # ============================================================
            logger.info("PROCESO [UpdateProfileView] - Fase: Validacion de datos")
            logger.info("PROCESO [UpdateProfileView] - Validando datos con UpdateProfileSerializer")
            
            # UpdateProfileSerializer tiene validaciones específicas para actualización
            serializer = UpdateProfileSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)  # Si falla, lanza excepción
            
            logger.info("SUCCESS [UpdateProfileView] - Datos validados correctamente")

            # ============================================================
            # FASE 2: ACTUALIZAR PERFIL VIA SERVICE
            # ============================================================
            logger.info("PROCESO [UpdateProfileView] - Fase: Ejecutando update_profile service")
            logger.info("PROCESO [UpdateProfileView] - Actualizando perfil en base de datos")
            
            # El servicio update_profile aplica la lógica de negocio
            # Maneja la actualización de avatar, bio, nombre, etc.
            user = update_profile(user=request.user, **serializer.validated_data)
            
            logger.info("SUCCESS [UpdateProfileView] - Perfil actualizado en BD")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [UpdateProfileView] - Perfil actualizado: {user_email}")
            logger.info("=" * 60)

            return Response(
                {
                    "message": "Perfil actualizado exitosamente",
                    "user": UserSerializer(user, context={'request': request}).data,
                },
                status=status.HTTP_200_OK,
            )
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [UpdateProfileView] - Error al actualizar perfil de: {user_email}")
            logger.error(f"ERROR [UpdateProfileView] - Motivo: {str(e)}")
            logger.error("=" * 60, exc_info=True)
            raise e


class ChangePasswordView(APIView):
    """
    Endpoint para cambiar la contraseña del usuario autenticado.
    
    Requiere:
    - Usuario autenticado
    - Cuenta activa
    - Contraseña actual (para verificación)
    - Nueva contraseña (con confirmación)
    """
    permission_classes = [IsAuthenticated, IsAccountActive]

    def patch(self, request):
        """
        Maneja la solicitud PATCH para cambiar la contraseña.
        """
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [ChangePasswordView] - Solicitud PATCH de cambio de contraseña")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: VALIDACION DE DATOS
            # ============================================================
            logger.info("PROCESO [ChangePasswordView] - Fase: Validacion de datos")
            logger.info("PROCESO [ChangePasswordView] - Validando datos con ChangePasswordSerializer")
            
            # ChangePasswordSerializer valida:
            # - Contraseña actual (verifica que coincida)
            # - Nueva contraseña (mínimo de caracteres, etc.)
            # - Confirmación de contraseña
            serializer = ChangePasswordSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            logger.info("SUCCESS [ChangePasswordView] - Datos validados correctamente")

            # ============================================================
            # FASE 2: CAMBIAR CONTRASEÑA
            # ============================================================
            logger.info("PROCESO [ChangePasswordView] - Fase: Cambiando contraseña en BD")
            logger.info("PROCESO [ChangePasswordView] - Ejecutando change_password service")
            
            # change_password aplica la lógica de negocio:
            # - Verifica la contraseña actual
            # - Hashea la nueva contraseña
            # - Guarda en la base de datos
            change_password(user=request.user, **serializer.validated_data)
            
            logger.info("SUCCESS [ChangePasswordView] - Contraseña actualizada en BD")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [ChangePasswordView] - Contraseña cambiada: {user_email}")
            logger.info("=" * 60)

            return Response(
                {
                    "message": "Contraseña cambiada exitosamente",
                },
                status=status.HTTP_200_OK,
            )
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [ChangePasswordView] - Error al cambiar contraseña de: {user_email}")
            logger.error(f"ERROR [ChangePasswordView] - Motivo: {str(e)}")
            logger.error("=" * 60, exc_info=True)
            raise e


class VerifyAccountView(APIView):
    """
    Endpoint para verificar la cuenta del usuario.
    Marca la cuenta como verificada (email confirmado).
    
    Requiere:
    - Usuario autenticado
    - Cuenta activa
    """
    permission_classes = [IsAuthenticated, IsAccountActive]

    def post(self, request):
        """
        Maneja la solicitud POST para verificar la cuenta.
        """
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [VerifyAccountView] - Solicitud POST de verificacion de cuenta")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: VERIFICAR CUENTA
            # ============================================================
            logger.info("PROCESO [VerifyAccountView] - Fase: Verificando cuenta")
            logger.info("PROCESO [VerifyAccountView] - Ejecutando verify_user service")
            
            # verify_user marca la cuenta como verificada (email_verified = True)
            user = verify_user(user=request.user)
            
            logger.info("SUCCESS [VerifyAccountView] - Cuenta verificada en BD")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [VerifyAccountView] - Cuenta verificada: {user_email}")
            logger.info("=" * 60)

            return Response(
                {
                    "message": "Cuenta verificada exitosamente",
                    "user": UserSerializer(user, context={'request': request}).data,
                },
                status=status.HTTP_200_OK,
            )
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [VerifyAccountView] - Error al verificar cuenta de: {user_email}")
            logger.error(f"ERROR [VerifyAccountView] - Motivo: {str(e)}")
            logger.error("=" * 60, exc_info=True)
            raise e


class DeactivateAccountView(APIView):
    """
    Endpoint para desactivar la cuenta del usuario.
    Marca la cuenta como inactiva (is_active = False).
    
    Requiere:
    - Usuario autenticado
    - Cuenta activa (para poder desactivarla)
    """
    permission_classes = [IsAuthenticated, IsAccountActive]

    def patch(self, request):
        """
        Maneja la solicitud PATCH para desactivar la cuenta.
        """
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [DeactivateAccountView] - Solicitud PATCH de desactivacion de cuenta")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: DESACTIVAR CUENTA
            # ============================================================
            logger.info("PROCESO [DeactivateAccountView] - Fase: Desactivando cuenta")
            logger.info("PROCESO [DeactivateAccountView] - Ejecutando deactivate_user service")
            
            # deactivate_user marca la cuenta como inactiva (is_active = False)
            user = deactivate_user(user=request.user)
            
            logger.info("SUCCESS [DeactivateAccountView] - Cuenta desactivada en BD")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [DeactivateAccountView] - Cuenta desactivada: {user_email}")
            logger.info("=" * 60)

            return Response(
                {
                    "message": "Cuenta desactivada exitosamente",
                    "user": UserSerializer(user, context={'request': request}).data,
                },
                status=status.HTTP_200_OK,
            )
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [DeactivateAccountView] - Error al desactivar cuenta de: {user_email}")
            logger.error(f"ERROR [DeactivateAccountView] - Motivo: {str(e)}")
            logger.error("=" * 60, exc_info=True)
            raise e


class ActivateAccountView(APIView):
    """
    Endpoint para activar la cuenta del usuario.
    Marca la cuenta como activa (is_active = True).
    
    Útil para usuarios que desactivaron su cuenta y quieren reactivarla.
    
    Requiere:
    - Usuario autenticado
    - No requiere que la cuenta esté activa (permite reactivación)
    """
    permission_classes = [IsAuthenticated]  # No requiere IsAccountActive (puede estar inactiva)

    def patch(self, request):
        """
        Maneja la solicitud PATCH para activar la cuenta.
        """
        user_email = request.user.email
        user_id = request.user.id
        
        # ============================================================
        # LOG: INICIO DE PETICION
        # ============================================================
        logger.info("=" * 60)
        logger.info("INICIO [ActivateAccountView] - Solicitud PATCH de activacion de cuenta")
        logger.info(f"Usuario: {user_email} (ID: {user_id})")
        logger.info("=" * 60)

        try:
            # ============================================================
            # FASE 1: ACTIVAR CUENTA
            # ============================================================
            logger.info("PROCESO [ActivateAccountView] - Fase: Activando cuenta")
            logger.info("PROCESO [ActivateAccountView] - Ejecutando activate_user service")
            
            # activate_user marca la cuenta como activa (is_active = True)
            user = activate_user(user=request.user)
            
            logger.info("SUCCESS [ActivateAccountView] - Cuenta activada en BD")

            # ============================================================
            # RESPUESTA EXITOSA
            # ============================================================
            logger.info("=" * 60)
            logger.info(f"FIN EXITOSO [ActivateAccountView] - Cuenta activada: {user_email}")
            logger.info("=" * 60)

            return Response(
                {
                    "message": "Cuenta activada exitosamente",
                    "user": UserSerializer(user, context={'request': request}).data,
                },
                status=status.HTTP_200_OK,
            )
            
        except Exception as e:
            # ============================================================
            # MANEJO DE ERRORES
            # ============================================================
            logger.error("=" * 60)
            logger.error(f"ERROR [ActivateAccountView] - Error al activar cuenta de: {user_email}")
            logger.error(f"ERROR [ActivateAccountView] - Motivo: {str(e)}")
            logger.error("=" * 60, exc_info=True)
            raise e
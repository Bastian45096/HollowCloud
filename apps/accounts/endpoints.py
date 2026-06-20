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

logger = logging.getLogger(__name__)

# Create your views here.

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

# Configuración del logger para este archivo
logger = logging.getLogger(__name__)

# apps/accounts/endpoints.py

# apps/accounts/endpoints.py

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info("INICIO [RegisterView] - Procesando solicitud POST de registro.")
        
        fase_actual = "Inicialización"

        try:
            # FASE 1: Validación
            fase_actual = "RegisterSerializer (Validación de datos)"
            logger.info(f"PROCESO [RegisterView] - [{fase_actual}] Validando datos de entrada.")
            
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # FASE 2: Creación de Usuario (el serializer lo hace)
            fase_actual = "create_user (Escritura en Base de Datos)"
            logger.info(f"PROCESO [RegisterView] - [{fase_actual}] Registrando la entidad.")
            
            # ✅ El serializer.create() guarda todo (incluyendo avatar y bio)
            user = serializer.save()

            # FASE 3: Generación de Tokens
            fase_actual = "generate_tokens (Servicio de Autenticación)"
            logger.info(f"PROCESO [RegisterView] - [{fase_actual}] Generando JSON Web Tokens.")
            
            tokens = generate_tokens(user=user)

            logger.info("RETORNO EXITOSO [RegisterView] - Flujo completado y respuesta enviada al cliente.")
            
            return Response(
                {
                    "message": "Usuario registrado exitosamente",
                    "user": UserSerializer(user).data,
                    "tokens": tokens,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(
                f"ERROR [RegisterView] - El proceso falló en la fase [{fase_actual}]. Motivo: {str(e)}", 
                exc_info=True
            )
            raise e


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Obtener IP del cliente
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        client_ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Login fallido - IP: {client_ip} - Error de validación")
            return Response(
                {"error": "Credenciales inválidas"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = authenticate_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                request=request
            )
            tokens = generate_tokens(user)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            logger.info(f"Login exitoso - IP: {client_ip} - User: {user.email}")
            return Response({
                "message": "Inicio de sesión exitoso",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            logger.warning(f"Login fallido - IP: {client_ip} - Credenciales inválidas")
            return Response(
                {"error": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

class LogoutView(APIView):

    permission_classes = [IsAuthenticated, IsAccountActive]

    def post(self, request):

        refresh_token = request.data.get("refresh")

        logout_user(refresh_token=refresh_token,)

        return Response({
            "message": "Cierre de sesión exitoso",

        },
        status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated, IsAccountActive]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        # Agregamos context={'request': request}
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        # Agregamos context={'request': request}
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated, IsAccountActive]
    # CRÍTICO: Permite a esta vista recibir el binario de la imagen
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        serializer = UpdateProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Tu servicio de negocio actualiza al usuario en la BD (incluyendo request.FILES si aplica)
        user = update_profile(user=request.user, **serializer.validated_data)

        return Response(
            {
                "message": "Perfil actualizado exitosamente",
                # Agregamos el contexto para que devuelva la URL absoluta de la foto sin romperse
                "user": UserSerializer(user, context={'request': request}).data,
            },
            status=status.HTTP_200_OK,
        )

class ChangePasswordView(APIView):

    permission_classes = [IsAuthenticated, IsAccountActive,]

    def patch(self, request):

        serializer = ChangePasswordSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        change_password(user=request.user, **serializer.validated_data)

        return Response(
            {
                "message": "Contraseña cambiada exitosamente",
            },
            status=status.HTTP_200_OK,
        )

class VerifyAccountView(APIView):

    permission_classes = [IsAuthenticated, IsAccountActive]

    def post(self, request):

        user = verify_user(user=request.user)

        return Response(
            {
                "message": "Cuenta verificada exitosamente",
                "user": UserSerializer(user).data,
            }
        )

class DeactivateAccountView(APIView):

    permission_classes = [IsAuthenticated, IsAccountActive]

    def patch(self, request):

        user = deactivate_user(user=request.user)

        return Response(
            {
                "message": "Cuenta desactivada exitosamente",
                "user": UserSerializer(user).data,
            }, status=status.HTTP_200_OK,
        )
    
class ActivateAccountView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request):

        user = activate_user(user=request.user)

        return Response(
            {
                "message": "Cuenta activada exitosamente",
                "user": UserSerializer(user).data,
            }, status=status.HTTP_200_OK,
        )
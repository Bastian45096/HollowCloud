# apps/accounts/serializers.py

"""
Serializers de la aplicación accounts.

Los serializers son responsables de:
1. Validar los datos de entrada (request.data)
2. Convertir datos complejos (modelos) a JSON
3. Convertir JSON a datos del modelo (creación/actualización)

Cada serializer tiene un propósito específico:
- UserSerializer: Devuelve datos del usuario (GET)
- RegisterSerializer: Valida y crea usuarios (POST /register)
- LoginSerializer: Valida credenciales (POST /login)
- ChangePasswordSerializer: Valida cambio de contraseña
- UpdateProfileSerializer: Valida actualización de perfil
"""

from django.core import validators
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Profile
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
import logging
from apps.accounts.services import create_user

logger = logging.getLogger(__name__)
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para devolver datos del usuario al frontend.
    
    Características:
    - Incluye campos del modelo User
    - Agrega campos calculados (avatar URL absoluta, profile)
    - Los campos son de solo lectura (no se pueden modificar con este serializer)
    
    Uso: GET /api/profile/, GET /api/auth/login/, etc.
    """
    
    # Campo calculado: obtiene la URL absoluta del avatar
    avatar = serializers.SerializerMethodField()
    
    # Campo calculado: obtiene datos del perfil (timezone, language)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User  # Modelo al que corresponde
        fields = [
            'id',           # UUID del usuario
            'email',        # Correo electrónico
            'username',     # Nombre de usuario único
            'first_name',   # Nombre
            'last_name',    # Apellido
            'bio',          # Biografía
            'avatar',       # URL del avatar (calculada)
            'is_verified',  # Si el email está verificado
            'created_at',   # Fecha de registro
            'profile',      # Datos del perfil (calculado)
        ]
        read_only_fields = fields  # Todos los campos son de solo lectura

    def get_avatar(self, obj):
        """
        Obtiene la URL absoluta del avatar.
        
        Por qué es necesario:
        - El frontend puede estar en otro puerto (ej: React en 3000, Django en 8000)
        - Una URL absoluta funciona desde cualquier lugar
        - Si usáramos URL relativa, el frontend pediría la imagen a su propio puerto (404)
        
        Ejemplo:
        - Sin context: "/media/avatars/dath.jpg" (relativa)
        - Con context: "http://localhost:8000/media/avatars/dath.jpg" (absoluta)
        """
        if obj.avatar:
            # Obtener la request del contexto (pasada en el view)
            request = self.context.get('request')
            if request:
                # Construye URL absoluta: http://dominio/media/avatar.jpg
                return request.build_absolute_uri(obj.avatar.url)
            # Fallback: URL relativa
            return obj.avatar.url
        return None

    def get_profile(self, obj):
        """
        Obtiene datos adicionales del perfil.
        
        El perfil contiene configuraciones del usuario como:
        - timezone: Zona horaria (ej: America/Santiago)
        - language: Idioma preferido (ej: es, en)
        """
        if hasattr(obj, 'profile') and obj.profile:
            return {
                "timezone": obj.profile.timezone,
                "language": obj.profile.language,
            }
        return None


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para registro de nuevos usuarios.
    
    Características:
    - Valida email único, username único
    - Valida contraseña con validate_password (mínimo 8 caracteres, etc.)
    - Confirma contraseña (password y password2)
    - Campos first_name y last_name son obligatorios
    - Bio y avatar son opcionales
    
    Uso: POST /api/register/
    """
    
    # Campo write_only: solo se recibe, no se devuelve
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)  # Confirmación de contraseña
    
    # Campos opcionales
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    avatar = serializers.ImageField(required=False, allow_null=True)
    
    # Campos obligatorios
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = [
            'email',        # Correo (obligatorio)
            'username',     # Nombre de usuario (obligatorio)
            'password',     # Contraseña (write_only)
            'password2',    # Confirmación (write_only)
            'first_name',   # Nombre (obligatorio)
            'last_name',    # Apellido (obligatorio)
            'bio',          # Biografía (opcional)
            'avatar',       # Avatar (opcional)
        ]

    def validate(self, attrs):
        """
        Validación a nivel de objeto (usa múltiples campos).
        
        Verifica que password y password2 coincidan.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs

    def validate_first_name(self, value):
        """
        Validación específica para el campo first_name.
        
        Verifica que:
        - No esté vacío
        - No tenga solo espacios
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es obligatorio")
        return value.strip()

    def validate_last_name(self, value):
        """
        Validación específica para el campo last_name.
        
        Verifica que:
        - No esté vacío
        - No tenga solo espacios
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El apellido es obligatorio")
        return value.strip()

    def validate_email(self, value):
        """
        Validación específica para el campo email.
        
        Verifica que:
        - No esté ya registrado (unicidad)
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("El email ya está en uso")
        return value

    def validate_username(self, value):
        """
        Validación específica para el campo username.
        
        Verifica que:
        - No esté ya registrado (unicidad)
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("El nombre de usuario ya está en uso")
        return value

    def create(self, validated_data):
        """
        Crea un nuevo usuario en la base de datos.
        
        Este método es llamado por serializer.save() en el view.
        
        Flujo:
        1. Eliminar password2 del diccionario (no es un campo del modelo)
        2. Extraer campos opcionales (avatar, bio)
        3. Llamar a create_user service con los datos validados
        4. El service crea el usuario (y el perfil asociado)
        """
        # password2 no es un campo del modelo, lo eliminamos
        validated_data.pop('password2')
        
        # Extraer campos opcionales
        avatar = validated_data.pop('avatar', None)
        bio = validated_data.pop('bio', '')
        
        # Llamar al servicio de creación de usuario
        # El service maneja la lógica de negocio:
        # - Crear el usuario
        # - Hashear la contraseña
        # - Crear el perfil asociado
        # - Manejar el avatar (si existe)
        user = create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data['first_name'], 
            last_name=validated_data['last_name'],   
            bio=bio,
            avatar=avatar,
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer para inicio de sesión.
    
    Características:
    - Valida email y password
    - No es un ModelSerializer (no guarda en BD)
    - Incluye validaciones de seguridad (prevención de inyección)
    - Normaliza email (lowercase, trim)
    
    Uso: POST /api/login/
    """
    
    email = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        """
        Validación específica para el campo email.
        
        Pasos de seguridad:
        1. Normalizar: lower() y strip()
        2. Validar formato de email (con validate_email)
        3. Prevenir caracteres peligrosos (inyección SQL, XSS)
        
        Por qué no usamos EmailField directamente:
        - Queremos control exacto sobre el mensaje de error
        - No queremos revelar si el email existe o no (seguridad)
        - Queremos validaciones extra de seguridad
        """
        # Normalizar
        value = value.lower().strip()
        
        # Validar formato (sin revelar si existe o no)
        try:
            validate_email(value)
        except DjangoValidationError:
            # Mensaje genérico por seguridad: no revelamos si el email es válido o no
            raise serializers.ValidationError("Credenciales inválidas")
        
        # Prevenir caracteres peligrosos (inyección SQL, XSS, etc.)
        # Esto es una capa extra de seguridad
        if any(c in value for c in ['<', '>', '\\', '"', "'", ';', '--']):
            raise serializers.ValidationError("Credenciales inválidas")
        
        return value

    def validate_password(self, value):
        """
        Validación específica para el campo password.
        
        Previene caracteres peligrosos que podrían causar:
        - Inyección SQL
        - XSS (Cross-Site Scripting)
        - Otros ataques de inyección
        """
        # Prevenir inyección
        if any(c in value for c in ['<', '>', '\\', '"', "'", ';', '--']):
            raise serializers.ValidationError("Credenciales inválidas")
        return value


class UserMinimalSerializer(serializers.ModelSerializer):
    """
    Serializer minimalista de usuario.
    
    Útil cuando solo necesitas información básica del usuario.
    Usado en el chat para mostrar el autor de un mensaje, etc.
    
    Uso: En el chat para mostrar información del autor de mensajes
    """
    
    class Meta:
        model = User
        fields = [
            'id',        # UUID del usuario
            'email',     # Correo electrónico
            'username',  # Nombre de usuario
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambio de contraseña.
    
    Características:
    - Valida la contraseña actual
    - Valida la nueva contraseña (mínimo 8 caracteres, etc.)
    - Campos write_only: no se devuelven al frontend
    
    Uso: PATCH /api/change-password/
    """
    
    current_password = serializers.CharField(write_only=True)
    
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password]  # Django password validation
    )


class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para actualización de perfil.
    
    Características:
    - Solo campos editables: first_name, last_name, bio, avatar
    - Permite actualización parcial (partial=True en el view)
    - Soporta archivos (avatar) gracias a MultiPartParser
    
    Uso: PATCH /api/update-profile/
    """
    
    class Meta:
        model = User
        fields = [
            'first_name',  # Nombre
            'last_name',   # Apellido
            'bio',         # Biografía
            'avatar',      # Avatar (imagen)
        ]
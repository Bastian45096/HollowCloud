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
    avatar = serializers.SerializerMethodField() 
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'bio',
            'avatar',
            'is_verified',
            'created_at',
            'profile',
        ]
        read_only_fields = fields

    def get_avatar(self, obj):
        """
        Retorna la URL absoluta del avatar si existe.
        """
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_profile(self, obj):
        """
        Retorna los datos del perfil si existe.
        """
        if hasattr(obj, 'profile') and obj.profile:
            return {
                "timezone": obj.profile.timezone,
                "language": obj.profile.language,
            }
        return None

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'password',
            'password2',
            'first_name',
            'last_name',
            'bio',
            'avatar',
        ]

    def validate(self, attrs):
        """Validar que las contraseñas coincidan"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs

    def validate_email(self, value):
        """Validar que el email sea único"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("El email ya está en uso")
        return value

    def validate_username(self, value):
        """Validar que el username sea único"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("El nombre de usuario ya está en uso")
        return value

    def create(self, validated_data):
        """
        Crear el usuario usando el servicio create_user.
         Elimina duplicación de código
         Centraliza la lógica de creación
         Reutiliza el servicio en otros lugares
        """
        # Eliminar password2 (solo para validación)
        validated_data.pop('password2')
        
        # Extraer avatar (si existe)
        avatar = validated_data.pop('avatar', None)
        
        # Extraer bio (si existe)
        bio = validated_data.pop('bio', '')
        
        logger.info(f"[RegisterSerializer] Creando usuario: {validated_data.get('username')}")
        logger.info(f"[RegisterSerializer] Bio: {bio}")
        logger.info(f"[RegisterSerializer] Avatar: {avatar.name if avatar else 'None'}")
        
       
        user = create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            bio=bio,
            avatar=avatar,
        )
        
        logger.info(f"[RegisterSerializer] Usuario creado exitosamente: {user.id}")
        
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        # Normalizar
        value = value.lower().strip()
        
        # Validar formato (sin revelar si existe o no)
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Credenciales inválidas")
        
        # Prevenir caracteres peligrosos
        if any(c in value for c in ['<', '>', '\\', '"', "'", ';', '--']):
            raise serializers.ValidationError("Credenciales inválidas")
        
        return value

    def validate_password(self, value):
        # Prevenir inyección
        if any(c in value for c in ['<', '>', '\\', '"', "'", ';', '--']):
            raise serializers.ValidationError("Credenciales inválidas")
        return value

class UserMinimalSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
        ]

class ChangePasswordSerializer(serializers.Serializer):

    current_password = serializers.CharField(write_only=True)

    new_password = serializers.CharField(
        write_only=True, validators=[validate_password])

class UpdateProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'bio',
            'avatar',
        ]
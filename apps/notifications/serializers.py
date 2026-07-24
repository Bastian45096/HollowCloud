# apps/notifications/serializers.py

"""
Serializers para la aplicación notifications.

Responsabilidades:
- Serializar notificaciones para el frontend
- Validar entrada para marcar notificaciones como leídas
- Serializar preferencias de notificaciones
"""

from rest_framework import serializers
from django.utils import timezone

from .models import Notification, NotificationPreference


import json
from rest_framework import serializers
from django.utils import timezone
from apps.notifications.models import Notification
from apps.chat.models import WorkspaceMember


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer principal para notificaciones.
    """
    
    # Campo adicional para mostrar el tipo en formato legible
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    
    # Campo calculado: tiempo transcurrido desde la creación
    time_ago = serializers.SerializerMethodField()
    
    # NUEVO CAMPO: datos parseados del mensaje (para invitaciones)
    parsed_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'title',
            'message',
            'notification_type',
            'notification_type_display',
            'is_read',
            'read_at',
            'created_at',
            'updated_at',
            'time_ago',
            'parsed_data',  # 🔥 AGREGADO
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'updated_at',
            'read_at',
            'time_ago',
            'notification_type_display',
            'parsed_data',  # 🔥 AGREGADO
        ]

    def get_time_ago(self, obj):
        """
        Calcula el tiempo transcurrido desde la creación de la notificación.
        
        Returns:
            str: Tiempo en formato legible (ej: "hace 5 minutos", "hace 2 horas", etc.)
        """
        if not obj.created_at:
            return None
        
        now = timezone.now()
        delta = now - obj.created_at
        
        # Días
        if delta.days > 0:
            if delta.days == 1:
                return 'hace 1 día'
            return f'hace {delta.days} días'
        
        # Horas
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            if hours == 1:
                return 'hace 1 hora'
            return f'hace {hours} horas'
        
        # Minutos
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            if minutes == 1:
                return 'hace 1 minuto'
            return f'hace {minutes} minutos'
        
        # Segundos
        else:
            return 'ahora mismo'
    
    def get_parsed_data(self, obj):
        """
        🔥 Intenta parsear el mensaje como JSON para extraer datos.
        
        Si el mensaje es un JSON válido, devuelve los datos parseados.
        Si no, devuelve un diccionario vacío.
        
        Returns:
            dict: Datos parseados o diccionario vacío
        """
        try:
            data = json.loads(obj.message)
            if isinstance(data, dict):
                # Aceptar TODOS los tipos de mensajes JSON (invitaciones, abandono, etc.)
                return data
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return {}


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer para preferencias de notificaciones.
    """
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id',
            'user',
            'email_enabled',
            'in_app_enabled',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'updated_at',
        ]


class MarkNotificationReadSerializer(serializers.Serializer):
    """
    Serializer para marcar notificaciones como leídas.
    """
    
    # Lista de IDs de notificaciones a marcar como leídas
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Lista de IDs de notificaciones a marcar como leídas"
    )
    
    # Si es True, marca TODAS las notificaciones como leídas
    mark_all = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Si es True, marca todas las notificaciones como leídas"
    )
    
    def validate(self, data):
        """
        Validación personalizada:
        - Si no se proporciona notification_ids y mark_all es False, error
        - Si se proporciona notification_ids y mark_all es True, error (conflicto)
        """
        notification_ids = data.get('notification_ids')
        mark_all = data.get('mark_all', False)
        
        if not mark_all and not notification_ids:
            raise serializers.ValidationError(
                "Debes proporcionar notification_ids o establecer mark_all=True"
            )
        
        if mark_all and notification_ids:
            raise serializers.ValidationError(
                "No puedes proporcionar notification_ids cuando mark_all=True"
            )
        
        return data


class UnreadCountSerializer(serializers.Serializer):
    """
    Serializer para el contador de notificaciones no leídas.
    """
    
    count = serializers.IntegerField(read_only=True)
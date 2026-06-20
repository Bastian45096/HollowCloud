from rest_framework.permissions import BasePermission
from .models import User

class IsOwner(BasePermission):

    
    """
    Permite acceso unicamente al propietario del recurso.
    """

    message = "No tienes permiso para acceder a este recurso."

    def has_object_permission(self, request, view, obj) -> bool:

        return obj == request.user

class IsVerified(BasePermission):

    """
    Permite acceso solo a usuarios verificados.
    """

    message = "Tu cuenta no está verificada. Por favor, verifica tu cuenta para acceder a este recurso."

    def has_permission(self, request, view) -> bool:

        return bool(
            request.user and
            request.user.is_authenticated 
            and request.user.is_verified
        )

class IsAccountActive(BasePermission):

    """
    Permite acceso solo a usuarios activos.
    """

    message = "Tu cuenta está inactiva. Por favor, contacta al soporte para más información."

    def has_permission(self, request, view) -> bool:

        return bool(
            request.user and
            request.user.is_authenticated 
            and request.user.is_active
        )

class IsSelfOrAdmin(BasePermission):

    """
    Permite acceso al propietario del recurso o a administradores.
    """

    message = "No tienes permiso para acceder a este recurso."

    def has_object_permission(self, request, view, obj) -> bool:

        return bool(
            obj == request.user or
            request.user.is_staff
        )
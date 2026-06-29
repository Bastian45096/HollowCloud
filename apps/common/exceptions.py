# apps/common/exceptions.py

class ApplicationError(Exception):
    """Excepción base para errores de la aplicación"""
    pass


class ValidationError(ApplicationError):
    """Error de validación de datos"""
    pass


class NotFoundError(ApplicationError):
    """Error cuando un recurso no se encuentra"""
    pass


class PermissionDeniedError(ApplicationError):
    """Error cuando el usuario no tiene permisos"""
    pass


class ConflictError(ApplicationError):
    """Error cuando hay un conflicto (ej: duplicado)"""
    pass


class BusinessLogicError(ApplicationError):
    """Error de lógica de negocio"""
    pass


class AuthenticationError(ApplicationError):
    """Error de autenticación"""
    pass
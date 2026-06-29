# apps/common/constants.py

# ============================================================
# ESTADOS GLOBALES
# ============================================================

class Status:
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    DELETED = 'deleted'
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


# ============================================================
# ROLES DE USUARIO
# ============================================================

class UserRole:
    ADMIN = 'admin'
    MODERATOR = 'moderator'
    MEMBER = 'member'
    GUEST = 'guest'


# ============================================================
# TIPOS DE CANALES
# ============================================================

class ChannelType:
    PUBLIC = 'public'
    PRIVATE = 'private'


# ============================================================
# LÍMITES
# ============================================================

MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB
MAX_MESSAGE_LENGTH = 10000
MAX_USERNAME_LENGTH = 150
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500


# ============================================================
# HTTP STATUS CODES (para referencia)
# ============================================================

class HttpStatus:
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500
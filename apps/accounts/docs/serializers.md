# Documentación de la Aplicación `accounts`
# Modulo: Serializers.py

La aplicación `accounts` gestiona todo lo relacionado con los usuarios del sistema HollowCloud, incluyendo su autenticación, perfiles y la integración con el panel de administración de Django.

## Modelos

### `User`

Este es el modelo de usuario personalizado de HollowCloud, extendiendo `AbstractUser` de Django y `BaseModel` para incluir campos `id` (UUID), `created_at` y `updated_at`. Utiliza el `email` como campo principal de autenticación.

-   **`email`**: `EmailField` único e indexado, utilizado como `USERNAME_FIELD`.
-   **`avatar`**: `ImageField` para la imagen de perfil del usuario, opcional.
-   **`bio`**: `TextField` para una breve biografía del usuario, opcional.
-   **`is_verified`**: `BooleanField` para indicar si la cuenta del usuario ha sido verificada, por defecto `False`.

**Campos Heredados de `AbstractUser`**: `username`, `first_name`, `last_name`, `is_staff`, `is_active`, `is_superuser`, `last_login`, `date_joined`, `groups`, `user_permissions`.

**Meta Opciones**:
-   `ordering = ["-created_at"]`: Ordena los usuarios por fecha de creación descendente.
-   `verbose_name = "User"`
-   `verbose_name_plural = "Users"`

### `Profile`

Este modelo almacena información adicional del usuario que no es directamente parte del modelo `User` principal, manteniendo una relación `OneToOneField` con `User`.

-   **`user`**: `OneToOneField` que enlaza con el modelo `User`, con `on_delete=models.CASCADE`.
-   **`timezone`**: `CharField` para la zona horaria del usuario, por defecto "America/Santiago".
-   **`language`**: `CharField` para el idioma preferido del usuario, por defecto "es".

**Meta Opciones**:
-   `ordering = ["-created_at"]`: Ordena los perfiles por fecha de creación descendente.
-   `verbose_name = "Profile"`
-   `verbose_name_plural = "Profiles"`

## Serializadores

### `UserSerializer`

Serializador para representar la información detallada de un usuario. Incluye un campo `profile` personalizado para mostrar la zona horaria y el idioma del usuario.

-   **`profile`**: `SerializerMethodField` que devuelve un diccionario con `timezone` y `language` del perfil asociado al usuario. Si no hay perfil, devuelve `None`.

**Campos**: `id`, `email`, `username`, `first_name`, `last_name`, `bio`, `avatar`, `is_verified`, `created_at`, `profile`.
**Campos de solo lectura**: Todos los campos listados.

### `RegisterSerializer`

Serializador utilizado para el registro de nuevos usuarios. Requiere `password` y `password2` para la validación.

-   **`password`**: `CharField` de solo escritura, con validación de contraseña de Django (`validate_password`).
-   **`password2`**: `CharField` de solo escritura, para confirmar la contraseña.

**Campos**: `email`, `username`, `password`, `password2`, `first_name`, `last_name`.

**Métodos Personalizados**:
-   **`validate(attrs)`**: Valida que `password` y `password2` coincidan. Lanza `serializers.ValidationError` si no es así.
-   **`create(validated_data)`**: Crea un nuevo usuario utilizando `User.objects.create_user` y establece la contraseña. También crea automáticamente un `Profile` asociado al nuevo usuario.

### `LoginSerializer`

Serializador básico para la autenticación de usuarios.

-   **`email`**: `EmailField` para el correo electrónico del usuario.
-   **`password`**: `CharField` de solo escritura para la contraseña.

### `UserMinimalSerializer`

Serializador para representar una versión mínima de la información de un usuario, útil para referencias rápidas.

**Campos**: `id`, `email`, `username`.

## Administración de Django

### `UserAdmin`

Clase de administración personalizada para el modelo `User`, que extiende `BaseUserAdmin` de Django para integrar el modelo de usuario personalizado.

-   **`list_display`**: Muestra `id`, `email`, `username`, `first_name`, `last_name`, `is_staff`, `is_active`, `is_verified`, `created_at`.
-   **`list_filter`**: Permite filtrar por `is_staff`, `is_superuser`, `is_active`, `is_verified`, `created_at`.
-   **`search_fields`**: Permite buscar por `email`, `username`, `first_name`, `last_name`.
-   **`ordering`**: Ordena los usuarios por `created_at` descendente.
-   **`readonly_fields`**: `id`, `created_at`, `updated_at`, `last_login`, `date_joined`.
-   **`fieldsets`**: Extiende los `fieldsets` predeterminados de `BaseUserAdmin` para incluir una sección "Información adicional" con `avatar`, `bio`, `is_verified`, `created_at`, `updated_at`.

### `ProfileAdmin`

Clase de administración para el modelo `Profile`.

-   **`list_display`**: Muestra `id`, `user`, `timezone`, `language`, `created_at`.
-   **`search_fields`**: Permite buscar por `user__email` y `user__username`.
-   **`readonly_fields`**: `id`, `created_at`, `updated_at`.
-   **`ordering`**: Ordena los perfiles por `created_at` descendente.

## Configuración

La aplicación `accounts` está configurada en `config/settings.py` con:

-   `AUTH_USER_MODEL = "accounts.User"`: Define el modelo `User` personalizado como el modelo de usuario predeterminado de Django.
-   `apps.accounts.apps.AccountsConfig` en `INSTALLED_APPS`.

## Uso

La aplicación `accounts` proporciona la base para la gestión de usuarios en HollowCloud. Los modelos y serializadores definidos aquí son fundamentales para la autenticación, registro y gestión de perfiles de usuario en la API REST.

Para la autenticación, se utiliza `rest_framework_simplejwt` con `JWTAuthentication`, lo que permite la emisión y validación de tokens JWT para usuarios registrados.

Los administradores pueden gestionar usuarios y sus perfiles a través del panel de administración de Django, con las configuraciones personalizadas para una mejor visualización y edición.
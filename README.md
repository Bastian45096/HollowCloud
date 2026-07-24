# HollowCloud

HollowCloud es una plataforma web construida actualmente como un monolito en Django, donde el backend, las vistas HTML y la lógica cliente en JavaScript conviven dentro del mismo proyecto. El sistema está organizado por dominios de negocio, expone una API interna consumida mediante `fetch` desde el frontend y ya tiene una base sólida para evolucionar en el futuro hacia una arquitectura con frontend desacoplado.

## Autor

**Bastian Andres Alfaro Valdebenito**

## Resumen del sistema

La aplicación implementa un enfoque de software modular sobre una base monolítica. A nivel funcional, hoy cubre autenticación de usuarios, perfil, workspaces colaborativos, canales, mensajería, invitaciones, notificaciones, almacenamiento de archivos y una base para workflows ejecutables.

Desde el punto de vista arquitectónico, el proyecto sigue un patrón híbrido:

- **Backend principal** en Django + Django REST Framework.
- **Frontend actual** renderizado desde Django Templates.
- **Lógica interactiva del cliente** escrita en JavaScript modular dentro de `static/js/`.
- **API interna** usada por el propio frontend mediante llamadas `fetch`.
- **Modelo de evolución futura** orientado a desacoplar el frontend sin rehacer el dominio ni la capa API.

## Objetivo arquitectónico

Hoy HollowCloud funciona como un **monolito modular**. Esta decisión es adecuada para una etapa de construcción rápida, control centralizado del dominio y menor complejidad operacional.

A futuro, el proyecto puede migrar hacia una arquitectura con frontend separado porque ya existe una separación razonable entre:

- vistas web,
- endpoints REST,
- servicios de dominio,
- selectores,
- serializadores,
- lógica cliente.

Eso permite que el backend actual actúe más adelante como **API platform** para una SPA o un frontend independiente, manteniendo el dominio y reduciendo el costo de migración.

## Stack tecnológico

### Backend

- `Django 5`
- `Django REST Framework`
- `Simple JWT`
- `Channels`
- `python-dotenv`
- `Pillow`
- `drf-spectacular`
- `django-xbench`

### Persistencia y datos

- `MySQL` como base de datos configurada actualmente
- soporte instalado para otros conectores en dependencias, aunque la configuración activa está orientada a MySQL

### Seguridad

- autenticación con JWT
- rotación de refresh tokens
- blacklist de tokens
- hash de contraseñas con `Argon2`
- middleware y constantes orientadas a mitigación de abuso y timing attacks

### Frontend actual

- Django Templates
- JavaScript vanilla modular
- CSS organizado por componentes, modales, base y responsive

## Arquitectura del proyecto

La solución está estructurada por apps de Django con separación funcional por dominio. La raíz del proyecto contiene configuración, apps de negocio, estáticos y media.

```text
HollowCloud/
├── apps/
│   ├── accounts/        # usuarios, login, registro, perfil
│   ├── api/             # agregador de rutas API
│   ├── audit/           # trazabilidad y registro de auditoría
│   ├── chat/            # workspaces, canales, mensajes, invitaciones
│   ├── common/          # modelos base, middleware, validaciones y excepciones
│   ├── notifications/   # notificaciones in-app y preferencias
│   ├── storage/         # carpetas, archivos, versionado y compartición
│   └── workflows/       # motor base para tareas y automatizaciones
├── config/              # settings, urls, asgi, wsgi
├── static/              # JavaScript, CSS e íconos
├── media/               # archivos subidos por usuarios
├── manage.py
└── requirements.txt
```

## Dominios funcionales en uso

### `accounts`

Gestiona el modelo de usuario personalizado, autenticación, registro, perfil, avatar y sesión. El sistema usa `accounts.User` como `AUTH_USER_MODEL`, con email único como identificador principal y soporte para perfil extendido.

Responsabilidades principales:

- registro de usuario
- login con JWT
- actualización de perfil
- logout
- notificación de bienvenida
- páginas web de `login`, `register`, `profile` y `dashboard`

### `chat`

Es el núcleo colaborativo del sistema. Implementa workspaces, membresías, roles, canales, mensajes e invitaciones. También incluye validaciones de membresía y gestión de privilegios sobre administradores y miembros.

Responsabilidades principales:

- creación y administración de workspaces
- canales por workspace
- envío, edición y eliminación de mensajes
- adjuntos de chat
- invitación, aceptación y rechazo de miembros
- promoción y reversión de administradores
- abandono o expulsión de usuarios

### `notifications`

Maneja el sistema de notificaciones internas. Está integrado con el flujo de negocio del chat y de cuentas, por ejemplo para bienvenida, eventos de workspace y cambios de rol.

Responsabilidades principales:

- listado de notificaciones
- marcado individual o masivo como leído
- eliminación
- resumen para dashboard
- preferencias de notificación

### `storage`

Representa la base del subsistema de archivos. Incluye carpetas jerárquicas, archivos, versionado y compartición entre usuarios.

Responsabilidades principales:

- carpetas por workspace
- archivos almacenados
- versiones de archivo
- compartición con permisos

### `audit`

Proporciona trazabilidad transversal mediante `AuditLog`, registrando acción, entidad afectada, metadata e IP de origen.

### `workflows`

Incluye un registro de tareas con patrón registry/singleton, validación de esquemas, hooks y tareas built-in. Esta parte da una base interesante para automatizaciones internas, integraciones o ejecución de procesos asíncronos a futuro.

## Diseño interno por capas

En varias apps se aprecia una organización orientada a capas de aplicación:

- `models.py`: entidades del dominio
- `serializers.py`: contratos de entrada/salida para API
- `selectors.py`: consultas y lectura especializada
- `services.py`: reglas de negocio y escritura
- `endpoints.py`: capa HTTP/REST
- `web_views.py`: vistas HTML renderizadas desde Django

Este enfoque mejora la mantenibilidad porque evita concentrar toda la lógica en vistas o serializers. También facilita la futura separación entre frontend y backend.

## Frontend actual

El frontend vive dentro del mismo proyecto Django, pero no está completamente acoplado al render del servidor. Hay una capa clara de JavaScript modular bajo `static/js/` que consume endpoints internos mediante `fetch`.

Las áreas visibles hoy son:

- autenticación y registro
- perfil de usuario
- dashboard
- chat colaborativo
- módulo de notificaciones

Estructura destacada:

- `static/js/chat-logic/`
- `static/js/notificaciones/`
- `static/js/logic-register.js`
- `apps/*/templates/`
- `static/css/`

## Integraciones `fetch` actualmente en uso

Una parte importante del sistema ya opera como si el frontend fuese un consumidor de API. Estas son las rutas que hoy están siendo consumidas desde el cliente.

### Cuentas y perfil

- `POST /api/APIVIEWCRTA/`  
  Registro de usuario

- `POST /api/APIVIEWLG/`  
  Inicio de sesión

- `GET /api/APIVIEWPRF/`  
  Obtención de perfil

- `PATCH /api/APIVIEWUPDATEPRF/`  
  Actualización de perfil

- `POST /api/APIVIEWLGT/`  
  Cierre de sesión

### Chat y colaboración

- `GET /api/chat/workspaces/`
- `POST /api/chat/workspaces/`
- `GET /api/chat/workspaces/<workspace_id>/`
- `PATCH /api/chat/workspaces/<workspace_id>/`
- `DELETE /api/chat/workspaces/<workspace_id>/`
- `GET /api/chat/workspaces/<workspace_id>/members/`
- `DELETE /api/chat/workspaces/<workspace_id>/members/`
- `GET /api/chat/workspaces/<workspace_id>/members/me/`
- `GET /api/chat/workspaces/<workspace_id>/channels/`
- `POST /api/chat/workspaces/<workspace_id>/channels/`
- `PATCH /api/chat/workspaces/<workspace_id>/channels/<channel_id>/`
- `DELETE /api/chat/workspaces/<workspace_id>/channels/<channel_id>/`
- `GET /api/chat/workspaces/<workspace_id>/channels/<channel_id>/messages/`
- `POST /api/chat/workspaces/<workspace_id>/channels/<channel_id>/messages/`
- `PATCH /api/chat/workspaces/<workspace_id>/channels/<channel_id>/messages/<message_id>/`
- `DELETE /api/chat/workspaces/<workspace_id>/channels/<channel_id>/messages/<message_id>/`
- `GET /api/chat/workspaces/search/?q=...`
- `POST /api/chat/workspaces/<workspace_id>/join/`
- `POST /api/chat/workspaces/<workspace_id>/invite/`
- `POST /api/chat/invitations/<membership_id>/accept/`
- `POST /api/chat/invitations/<membership_id>/reject/`
- `POST /api/chat/workspaces/<workspace_id>/promote-admin/`
- `POST /api/chat/workspaces/<workspace_id>/revert-admin/`
- `POST /api/chat/workspaces/<workspace_id>/leave/`

### Notificaciones

- `GET /api/notifications/?limit=100`
- `PATCH /api/notifications/mark-read/`
- `GET /api/notifications/<notification_id>/`
- `DELETE /api/notifications/<notification_id>/`
- `GET /api/notifications/preferences/`
- `PATCH /api/notifications/preferences/`
- `GET /api/notifications/summary/`
- `PATCH /api/notifications/<notification_id>/read/`

## Flujo de autenticación

El sistema está diseñado alrededor de JWT y almacenamiento del token en `localStorage`, con lógica cliente para reintento y refresco de sesión.

Flujo actual:

1. el usuario inicia sesión o se registra
2. el backend emite `access` y `refresh token`
3. el frontend guarda ambos tokens en `localStorage`
4. las llamadas `fetch` incluyen `Authorization: Bearer <token>`
5. cuando una petición responde `401`, la capa `api.js` intenta refrescar el token
6. si el refresco falla, el usuario es redirigido a `login`

Esto muestra que la aplicación ya tiene una semántica compatible con frontend desacoplado, aunque todavía se sirva desde el mismo proyecto Django.

## Modelos de dominio relevantes

### Identidad

- `User`
- `Profile`

### Colaboración

- `Workspace`
- `WorkspaceMember`
- `Channel`
- `Message`

### Notificaciones

- `Notification`
- `NotificationPreference`

### Almacenamiento

- `Folder`
- `StoredFile`
- `FileVersion`
- `FileShare`

### Observabilidad y base

- `AuditLog`
- `BaseModel`
- `UUIDModel`
- `TimeStampedModel`
- `SoftDeleteModel`

## Puntos fuertes del diseño actual

- separación razonable entre dominio, endpoints y vistas
- modelo de usuario personalizado correctamente definido
- base REST suficiente para crecimiento del frontend
- trazabilidad mediante logging detallado
- estructura modular por bounded contexts
- soporte de notificaciones integrado al flujo de negocio
- motor inicial de workflows con capacidad de expansión
- uso de UUIDs en entidades base

## Consideraciones técnicas detectadas

Durante la inspección del código se observan algunos puntos que conviene alinear para consolidar la arquitectura:

- el frontend de chat intenta refrescar tokens con `POST /api/token/refresh/`, mientras la ruta registrada en la API es `POST /api/auth/refresh/`
- `static/js/chat-logic/auth.js` consulta `GET /api/accounts/me/`, pero esa ruta no aparece registrada actualmente en `apps/api/urls.py`
- existen endpoints históricos con nombres como `APIVIEWLG`, `APIVIEWPRF` o `APIVIEWCRTA`; funcionalmente sirven, pero a nivel de diseño API sería recomendable migrarlos gradualmente a rutas más semánticas

Ninguno de estos puntos invalida la base del proyecto, pero sí marcan una buena línea de mejora para la siguiente etapa de madurez.

## Visión de evolución

La mejor evolución para HollowCloud no es rehacer el sistema, sino reforzar la frontera entre presentación y servicios.

Un camino natural sería:

1. estabilizar y normalizar contratos REST
2. completar endpoints faltantes usados por el cliente
3. desacoplar la lógica visual del template server-rendered
4. mover el frontend a una SPA o cliente independiente
5. conservar Django como backend de dominio, autenticación, permisos y persistencia

Esto permitiría escalar la experiencia de usuario sin perder la inversión ya hecha en el dominio ni en la API interna.

## Configuración local

### Requisitos

- Python `3.11+`
- MySQL
- archivo `.env` en la raíz del proyecto

### Variables esperadas

Según la configuración actual, el proyecto espera al menos:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

### Instalación

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Rutas web principales

- `/login/`
- `/register/`
- `/accounts/dashboard/`
- `/profile/`
- `/chat/`
- `/notificaciones/`

## Estado de madurez

HollowCloud ya no es una prueba aislada ni una maqueta plana. La estructura actual muestra decisiones de ingeniería reales: separación modular, autenticación robusta, dominio colaborativo, API interna reutilizable y componentes listos para escalar.

La base es suficientemente buena para seguir iterando como monolito productivo hoy, y suficientemente ordenada para convertirse mañana en una plataforma con frontend independiente.

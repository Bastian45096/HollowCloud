import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from apps.storage import services

from .models import Folder, StoredFile, Workspace
from .serializers import (
    CreateFolderInputSerializer, 
    UploadFileInputSerializer, 
    UpdateVersionInputSerializer,
    FolderOutputSerializer,
    StoredFileOutputSerializer,
    FileVersionOutputSerializer
)
from apps.storage.services import (
    StorageServiceError, 
    FolderNotFoundError, 
    FileExistsError, 
    InvalidFileNameError
)

# Logger dedicado para el módulo de Storage
logger = logging.getLogger(__name__)

class StorageContentView(APIView):
    """
    Endpoint: GET /api/storage/<workspace_id>/items/?folder_id=<id>
    Responsabilidad: Listar carpetas y archivos con trazabilidad completa.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        # ============================================================
        # 1. LOG DE INICIO Y CONTEXTO
        # ============================================================
        folder_id = request.query_params.get('folder_id')
        
        logger.info("=" * 80)
        logger.info(f"[STORAGE-LIST] Iniciando listado de contenido")
        logger.info(f"[STORAGE-LIST] Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"[STORAGE-LIST] Workspace ID: {workspace_id}")
        logger.info(f"[STORAGE-LIST] Carpeta Padre ID: {folder_id if folder_id else 'Raíz'}")
        logger.info("=" * 80)

        try:
            # ============================================================
            # 2. OBTENCIÓN DE ENTIDAD BASE
            # ============================================================
            workspace = get_object_or_404(Workspace, id=workspace_id)
            logger.debug(f"[STORAGE-LIST] Workspace encontrado: {workspace.name}")

            # ============================================================
            # 3. EJECUCIÓN DEL SERVICIO
            # ============================================================
            logger.debug("[STORAGE-LIST] Ejecutando servicio get_folder_contents_service...")
            data = services.get_folder_contents_service(workspace=workspace, folder_id=folder_id)
            
            folders_count = len(data['folders'])
            files_count = len(data['files'])
            logger.info(f"[STORAGE-LIST] Servicio completado. Carpetas: {folders_count}, Archivos: {files_count}")

            # ============================================================
            # 4. SERIALIZACIÓN Y RESPUESTA
            # ============================================================
            # Serialización manual controlada para garantizar formato exacto
            folders_serialized = [
                {'id': f.id, 'name': f.name, 'type': 'folder', 'created_at': f.created_at}
                for f in data['folders']
            ]
            files_serialized = [
                {
                    'id': f.id, 'name': f.name, 'type': 'file',
                    'mime_type': f.mime_type, 'size': f.size,
                    'version': f.current_version, 'uploaded_by': f.uploaded_by.email,
                    'created_at': f.created_at, 'url': f.file.url if f.file else None
                }
                for f in data['files']
            ]
            
            response_data = {'folders': folders_serialized, 'files': files_serialized}
            
            logger.info(f"[STORAGE-LIST] Respuesta enviada exitosamente (Status 200)")
            logger.info("=" * 80)
            
            return Response(response_data)

        except Exception as e:
            # ============================================================
            # 5. MANEJO DE ERRORES CRÍTICOS
            # ============================================================
            logger.error("=" * 80)
            logger.error(f"[STORAGE-LIST] ❌ ERROR CRÍTICO al listar contenido")
            logger.error(f"[STORAGE-LIST] Usuario: {request.user.email}")
            logger.error(f"[STORAGE-LIST] Error: {str(e)}", exc_info=True)
            logger.error("=" * 80)
            
            return Response({'error': 'Error interno al cargar contenido'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateFolderView(APIView):
    """
    Endpoint: POST /api/storage/<workspace_id>/folders/
    Responsabilidad: Crear carpeta con validación estricta y logs de auditoría.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        # ============================================================
        # 1. LOG DE INICIO
        # ============================================================
        logger.info("=" * 80)
        logger.info(f"[STORAGE-CREATE-FOLDER] Iniciando creación de carpeta")
        logger.info(f"[STORAGE-CREATE-FOLDER] Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"[STORAGE-CREATE-FOLDER] Workspace ID: {workspace_id}")
        logger.info(f"[STORAGE-CREATE-FOLDER] Datos brutos: {request.data}")
        logger.info("=" * 80)

        try:
            workspace = get_object_or_404(Workspace, id=workspace_id)
            
            # ============================================================
            # 2. VALIDACIÓN DE ENTRADA (SERIALIZER)
            # ============================================================
            serializer = CreateFolderInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            logger.debug(f"[STORAGE-CREATE-FOLDER] Validación de entrada exitosa: {serializer.validated_data}")

            # Preparar argumentos complejos
            parent = None
            if serializer.validated_data.get('parent_id'):
                parent = get_object_or_404(Folder, id=serializer.validated_data['parent_id'], workspace=workspace)
                logger.debug(f"[STORAGE-CREATE-FOLDER] Carpeta padre encontrada: {parent.name}")

            # ============================================================
            # 3. EJECUCIÓN DEL SERVICIO
            # ============================================================
            logger.info(f"[STORAGE-CREATE-FOLDER] Ejecutando lógica de negocio (create_folder_service)...")
            folder = services.create_folder_service(
                workspace=workspace,
                name=serializer.validated_data['name'],
                parent=parent,
                created_by=request.user
            )
            logger.info(f"[STORAGE-CREATE-FOLDER] ✅ Carpeta creada exitosamente. ID: {folder.id}, Nombre: {folder.name}")

            # ============================================================
            # 4. RESPUESTA EXITOSA
            # ============================================================
            response_data = FolderOutputSerializer(folder).data
            logger.info(f"[STORAGE-CREATE-FOLDER] Respuesta enviada (Status 201)")
            logger.info("=" * 80)
            
            return Response(response_data, status=status.HTTP_201_CREATED)

        except (InvalidFileNameError, FileExistsError) as e:
            # Errores de Regla de Negocio (Cliente)
            logger.warning(f"[STORAGE-CREATE-FOLDER] ⚠️ Error de validación de negocio: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Errores Inesperados (Servidor)
            logger.error("=" * 80)
            logger.error(f"[STORAGE-CREATE-FOLDER] ❌ ERROR INESPERADO")
            logger.error(f"[STORAGE-CREATE-FOLDER] Error: {str(e)}", exc_info=True)
            logger.error("=" * 80)
            return Response({'error': 'Error interno al crear la carpeta'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UploadFileView(APIView):
    """
    Endpoint: POST /api/storage/<workspace_id>/upload/
    Responsabilidad: Subida segura de archivos con detección MIME y versionado inicial.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        # ============================================================
        # 1. LOG DE INICIO
        # ============================================================
        logger.info("=" * 80)
        logger.info(f"[STORAGE-UPLOAD] Iniciando subida de archivo")
        logger.info(f"[STORAGE-UPLOAD] Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"[STORAGE-UPLOAD] Workspace ID: {workspace_id}")
        
        file_obj = request.data.get('file')
        file_name = file_obj.name if file_obj else 'N/A'
        file_size = file_obj.size if file_obj else 0
        logger.info(f"[STORAGE-UPLOAD] Archivo recibido: {file_name} ({file_size} bytes)")
        logger.info("=" * 80)

        try:
            workspace = get_object_or_404(Workspace, id=workspace_id)
            
            # ============================================================
            # 2. VALIDACIÓN DE ENTRADA
            # ============================================================
            serializer = UploadFileInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            logger.debug(f"[STORAGE-UPLOAD] Validación de archivo y tamaño exitosa")

            folder = None
            if serializer.validated_data.get('folder_id'):
                folder = get_object_or_404(Folder, id=serializer.validated_data['folder_id'], workspace=workspace)
                logger.debug(f"[STORAGE-UPLOAD] Destino: Carpeta ID {folder.id}")

            # ============================================================
            # 3. EJECUCIÓN DEL SERVICIO
            # ============================================================
            logger.info(f"[STORAGE-UPLOAD] Procesando archivo (detección MIME, guardado, versión 1)...")
            stored_file = services.upload_file_service(
                workspace=workspace,
                folder=folder,
                file_obj=serializer.validated_data['file'],
                uploaded_by=request.user
            )
            logger.info(f"[STORAGE-UPLOAD] ✅ Archivo subido exitosamente. ID: {stored_file.id}, URL: {stored_file.file.url}")

            # ============================================================
            # 4. RESPUESTA EXITOSA
            # ============================================================
            response_data = StoredFileOutputSerializer(stored_file, context={'request': request}).data
            logger.info(f"[STORAGE-UPLOAD] Respuesta enviada (Status 201)")
            logger.info("=" * 80)
            
            return Response(response_data, status=status.HTTP_201_CREATED)

        except (InvalidFileNameError, FileExistsError) as e:
            logger.warning(f"[STORAGE-UPLOAD] ⚠️ Error de negocio: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"[STORAGE-UPLOAD] ❌ ERROR CRÍTICO EN SUBIDA")
            logger.error(f"[STORAGE-UPLOAD] Error: {str(e)}", exc_info=True)
            logger.error("=" * 80)
            return Response({'error': 'Error interno al subir el archivo'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateFileVersionView(APIView):
    """
    Endpoint: POST /api/storage/<workspace_id>/files/<file_id>/version/
    Responsabilidad: Actualizar versión manteniendo historial inmutable.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, file_id):
        # ============================================================
        # 1. LOG DE INICIO
        # ============================================================
        logger.info("=" * 80)
        logger.info(f"[STORAGE-VERSION] Iniciando actualización de versión")
        logger.info(f"[STORAGE-VERSION] Usuario: {request.user.email} (ID: {request.user.id})")
        logger.info(f"[STORAGE-VERSION] Workspace ID: {workspace_id}")
        logger.info(f"[STORAGE-VERSION] Archivo Objetivo ID: {file_id}")
        logger.info("=" * 80)

        try:
            workspace = get_object_or_404(Workspace, id=workspace_id)
            stored_file = get_object_or_404(StoredFile, id=file_id, workspace=workspace)
            
            logger.debug(f"[STORAGE-VERSION] Archivo actual encontrado: {stored_file.name} (Versión actual: {stored_file.current_version})")

            # ============================================================
            # 2. VALIDACIÓN DE ENTRADA
            # ============================================================
            serializer = UpdateVersionInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            logger.debug(f"[STORAGE-VERSION] Nuevo archivo válido para versionado")

            # ============================================================
            # 3. EJECUCIÓN DEL SERVICIO
            # ============================================================
            logger.info(f"[STORAGE-VERSION] Ejecutando update_file_version_service...")
            new_version = services.update_file_version_service(
                stored_file=stored_file,
                file_obj=serializer.validated_data['file'],
                uploaded_by=request.user
            )
            logger.info(f"[STORAGE-VERSION] ✅ Nueva versión creada: #{new_version.version_number}")

            # ============================================================
            # 4. RESPUESTA EXITOSA
            # ============================================================
            response_data = FileVersionOutputSerializer(new_version).data
            logger.info(f"[STORAGE-VERSION] Respuesta enviada (Status 200)")
            logger.info("=" * 80)
            
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"[STORAGE-VERSION] ❌ ERROR AL ACTUALIZAR VERSIÓN")
            logger.error(f"[STORAGE-VERSION] Error: {str(e)}", exc_info=True)
            logger.error("=" * 80)
            return Response({'error': 'Error interno al actualizar la versión'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReplaceFileView(APIView):
    """
    Endpoint: POST /api/storage/<workspace_id>/files/<file_id>/replace/
    Responsabilidad: Reemplazar completamente un archivo (nombre, tipo, contenido).
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, file_id):
        logger.info("=" * 80)
        logger.info(f"[STORAGE-REPLACE] Iniciando reemplazo de archivo")
        logger.info(f"[STORAGE-REPLACE] Usuario: {request.user.email}")
        logger.info(f"[STORAGE-REPLACE] Archivo ID: {file_id}")
        logger.info("=" * 80)

        try:
            workspace = get_object_or_404(Workspace, id=workspace_id)
            stored_file = get_object_or_404(StoredFile, id=file_id, workspace=workspace)

            # Validar que se envió un archivo
            if not request.data.get('file'):
                return Response({'error': 'No se proporcionó ningún archivo'}, status=400)

            # Ejecutar servicio
            updated_file = services.replace_file(
                stored_file=stored_file,
                new_file_obj=request.data['file'],
                uploaded_by=request.user
            )

            logger.info(f"[STORAGE-REPLACE] ✅ Archivo reemplazado: {updated_file.name} ({updated_file.mime_type})")
            
            # Devolver el objeto completo actualizado para que el frontend refresque el icono
            return Response(
                StoredFileOutputSerializer(updated_file, context={'request': request}).data, 
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"[STORAGE-REPLACE] ❌ ERROR: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=500)
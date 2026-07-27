import os
import magic
from typing import Optional, Any, Dict, List
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from .models import Folder, StoredFile, FileVersion
from apps.accounts.models import User
from apps.chat.models import Workspace

class StorageServiceError(Exception):
    """Excepción base para errores de lógica en Storage."""
    pass

class FolderNotFoundError(StorageServiceError):
    pass

class FileExistsError(StorageServiceError):
    pass

class InvalidFileNameError(StorageServiceError):
    pass

def _detect_mime_type(file_path: str) -> str:
    """Detecta el tipo MIME real del archivo usando libmagic."""
    try:
        if not file_path or not os.path.exists(file_path):
            return "application/octet-stream"
        mime = magic.Magic(mime=True)
        return mime.from_file(file_path)
    except Exception:
        return "application/octet-stream"

@transaction.atomic
def create_folder_service(
    workspace: Workspace,
    name: str,
    parent: Optional[Folder],
    created_by: User
) -> Folder:
    """
    Crea una carpeta.
    Retorna: Objeto Folder creado.
    Raises: InvalidFileNameError, FileExistsError
    """
    name = name.strip()
    if not name:
        raise InvalidFileNameError("El nombre de la carpeta no puede estar vacío")

    if Folder.objects.filter(workspace=workspace, parent=parent, name=name).exists():
        raise FileExistsError("Ya existe una carpeta con este nombre en esta ubicación")

    return Folder.objects.create(
        workspace=workspace,
        parent=parent,
        name=name
    )

@transaction.atomic
def upload_file_service(
    workspace: Workspace,
    folder: Optional[Folder],
    file_obj: Any,
    uploaded_by: User
) -> StoredFile:
    """
    Sube un nuevo archivo.
    Retorna: Objeto StoredFile creado.
    Raises: InvalidFileNameError, FileExistsError
    """
    original_name = file_obj.name.strip()
    if not original_name:
        raise InvalidFileNameError("El archivo debe tener un nombre válido")

    if StoredFile.objects.filter(workspace=workspace, folder=folder, name=original_name).exists():
        raise FileExistsError(f"Ya existe un archivo llamado '{original_name}'. Usa 'Actualizar Versión' para reemplazarlo.")

    temp_path = file_obj.temporary_file_path() if hasattr(file_obj, 'temporary_file_path') else None
    mime_type = _detect_mime_type(temp_path) if temp_path else getattr(file_obj, 'content_type', "application/octet-stream")
    
    stored_file = StoredFile.objects.create(
        workspace=workspace,
        folder=folder,
        uploaded_by=uploaded_by,
        name=original_name,
        file=file_obj,
        mime_type=mime_type,
        size=file_obj.size,
        current_version=1
    )

    FileVersion.objects.create(
        stored_file=stored_file,
        version_number=1,
        file=stored_file.file,
        uploaded_by=uploaded_by,
        size=file_obj.size
    )

    return stored_file

@transaction.atomic
def update_file_version_service(
    stored_file: StoredFile,
    file_obj: Any,
    uploaded_by: User
) -> FileVersion:
    """
    Sube una nueva versión.
    Retorna: Objeto FileVersion creado.
    """
    new_version_number = stored_file.current_version + 1
    
    temp_path = file_obj.temporary_file_path() if hasattr(file_obj, 'temporary_file_path') else None
    mime_type = _detect_mime_type(temp_path) if temp_path else getattr(file_obj, 'content_type', stored_file.mime_type)

    new_version = FileVersion.objects.create(
        stored_file=stored_file,
        version_number=new_version_number,
        file=file_obj,
        uploaded_by=uploaded_by,
        size=file_obj.size
    )

    stored_file.file = file_obj
    stored_file.mime_type = mime_type
    stored_file.size = file_obj.size
    stored_file.current_version = new_version_number
    stored_file.save(update_fields=['file', 'mime_type', 'size', 'current_version', 'updated_at'])

    return new_version

def get_folder_contents_service(
    workspace: Workspace,
    folder_id: Optional[int] = None
) -> Dict[str, List]:
    """
    Obtiene contenido.
    Retorna: Diccionario con listas de carpetas e archivos.
    """
    folders_qs = Folder.objects.filter(
        workspace=workspace, 
        parent_id=folder_id
    ).order_by('name')
    
    files_qs = StoredFile.objects.filter(
        workspace=workspace, 
        folder_id=folder_id
    ).select_related('uploaded_by').order_by('-created_at')

    # Retornamos datos crudos, el serializer los formateará si es necesario, 
    # pero usualmente para listas complejas el View construye la respuesta directa o usa un serializer simple
    return {
        'folders': list(folders_qs),
        'files': list(files_qs)
    }

@transaction.atomic
def replace_file(
    *,
    stored_file: StoredFile,
    new_file_obj: Any,
    uploaded_by: User
) -> StoredFile:
    """
    Reemplaza el archivo actual por uno nuevo (cambia nombre, tipo, tamaño).
    Crea una nueva versión con el nuevo archivo, pero actualiza el puntero principal.
    """
    import os
    import magic
    
    # 1. Detectar nuevos metadatos
    temp_path = new_file_obj.temporary_file_path() if hasattr(new_file_obj, 'temporary_file_path') else None
    mime_type = _detect_mime_type(temp_path) if temp_path else getattr(new_file_obj, 'content_type', "application/octet-stream")
    new_name = new_file_obj.name.strip()
    new_size = new_file_obj.size

    # 2. Crear nueva versión (Historial)
    # Nota: El número de versión sigue siendo consecutivo, pero este salto es cualitativo
    new_version_number = stored_file.current_version + 1
    
    FileVersion.objects.create(
        stored_file=stored_file,
        version_number=new_version_number,
        file=new_file_obj,
        uploaded_by=uploaded_by,
        size=new_size
    )

    # 3. Actualizar el archivo PRINCIPAL con los nuevos datos
    stored_file.name = new_name
    stored_file.file = new_file_obj
    stored_file.mime_type = mime_type
    stored_file.size = new_size
    stored_file.current_version = new_version_number
    stored_file.save(update_fields=['name', 'file', 'mime_type', 'size', 'current_version', 'updated_at'])

    return stored_file
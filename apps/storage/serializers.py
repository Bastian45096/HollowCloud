from rest_framework import serializers
from .models import Folder, StoredFile, FileVersion

# --- INPUT SERIALIZERS (Validación) ---

class CreateFolderInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("El nombre no puede estar vacío")
        return value.strip()

class UploadFileInputSerializer(serializers.Serializer):
    file = serializers.FileField()
    
    # CAMBIO AQUÍ: Usar CharField en lugar de IntegerField para soportar UUIDs y Null
    folder_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate_file(self, value):
        MAX_SIZE = 50 * 1024 * 1024  # 50MB
        if value.size > MAX_SIZE:
            raise serializers.ValidationError("El archivo excede el límite de 50MB")
        return value

    def validate_folder_id(self, value):
        # Si viene vacío o null, lo dejamos así (significa carpeta raíz)
        if not value:
            return None
        # Si tiene valor, retornamos el string (UUID) tal cual para que la vista lo procese
        return value

class UpdateVersionInputSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        MAX_SIZE = 50 * 1024 * 1024
        if value.size > MAX_SIZE:
            raise serializers.ValidationError("El archivo excede el límite de 50MB")
        return value

# --- OUTPUT SERIALIZERS (Respuesta) ---

class FolderOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent', 'created_at']

class FileVersionOutputSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    
    class Meta:
        model = FileVersion
        fields = ['id', 'version_number', 'size', 'uploaded_by_email', 'created_at']

class StoredFileOutputSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = StoredFile
        fields = [
            'id', 'name', 'folder', 'mime_type', 'size', 
            'current_version', 'uploaded_by_email', 'file', 
            'download_url', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'size', 'current_version', 'mime_type']

    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

class StorageContentOutputSerializer(serializers.Serializer):
    """Serializer compuesto para la lista de contenido"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()
    created_at = serializers.DateTimeField()
    # Campos específicos opcionales
    mime_type = serializers.CharField(required=False)
    size = serializers.IntegerField(required=False)
    version = serializers.IntegerField(required=False)
    uploaded_by = serializers.CharField(required=False, source='uploaded_by.email')
    url = serializers.URLField(required=False, source='file.url')
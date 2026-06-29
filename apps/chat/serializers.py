from rest_framework import serializers
from django.utils.text import slugify

from apps.accounts.serializers import UserSerializer
from apps.chat.models import Workspace, WorkspaceMember, Channel, Message, MessageAttachment

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """
    Serializador para miembros de un workspace
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:

        model = WorkspaceMember
        fields = [
            'id',
            'user',
            'user_id',
            'role',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

# apps/chat/serializers.py

class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializador para workspaces"""

    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            'id',
            'name',
            'slug',
            'owner',
            'description',
            'member_count',
            'is_member',
            'user_role',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True} 
        }
    
    def get_member_count(self, obj) -> int:
        return obj.memberships.count()

    def get_is_member(self, obj) ->bool:

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.memberships.filter(user=request.user).exists()
        return False

    def get_user_role(self, obj) -> str:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = obj.memberships.filter(user=request.user).first()
            return membership.role if membership else 'member'
        return 'member'

    def create(self, validated_data):
        """Crear workspace con slug automatico"""
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        
        return super().create(validated_data)

class WorkspaceDetailSerializer(WorkspaceSerializer):
    """Serializador detallado de workspace con miembros y canales"""

    members = serializers.SerializerMethodField()
    channels = serializers.SerializerMethodField()

    class Meta(WorkspaceSerializer.Meta):
        fields = WorkspaceSerializer.Meta.fields + ['members', 'channels']

    def get_members(self, obj):
        members = obj.memberships.select_related('user').all()
        return WorkspaceMemberSerializer(members, many=True).data

    
    def get_channels(self, obj):
        channels = obj.channels.all()
        return ChannelSerializer(channels, many=True, context=self.context).data


# apps/chat/serializers.py

class ChannelSerializer(serializers.ModelSerializer):
    """Serializador para canales"""

    workspace = WorkspaceSerializer(read_only=True)
    workspace_id = serializers.UUIDField(write_only=True, required=False) 
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'slug', 'workspace', 'workspace_id',
            'channel_type', 'description', 'message_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True},
            'workspace_id': {'required': False} 
        }

    def get_message_count(self, obj) -> int:
        return obj.messages.count()

    def create(self, validated_data):
        """Crear canal con slug automatico"""
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        return super().create(validated_data)

class ChannelDetailSerializer(ChannelSerializer):

    """
    Serializador detallado de canal con mensajes recientes
    """

    recent_messages = serializers.SerializerMethodField()

    class Meta(ChannelSerializer.Meta):
        fields = ChannelSerializer.Meta.fields + ['recent_messages']

    def get_recent_messages(self, obj):
        messages = obj.messages.select_related('author').order_by('-created_at')[:5:0]
        return MessageSerializer(messages, many=True).data

class MessageAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializador para adjuntos de mensajes
    """

    file_url = serializers.SerializerMethodField()

    class Meta:

        model = MessageAttachment
        fields = ['id', 'file', 'file_url', 'original_name', 'mime_type', 'size', 'created_at']

        read_only_fields = ['id', 'created_at']

    def get_file_url(self, obj):

        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

# apps/chat/serializers.py

# apps/chat/serializers.py

class MessageSerializer(serializers.ModelSerializer):
    """
    Serializador para mensajes con avatar del autor
    """

    author = serializers.SerializerMethodField()  
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    attachment_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'channel', 'author', 'content', 'attachments',
            'attachment_count', 'edited_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'edited_at', 'created_at', 'updated_at']

    
    def get_author(self, obj):
        request = self.context.get('request')
        user = obj.author
        
        avatar_url = None
        if user.avatar:
            if request:
                avatar_url = request.build_absolute_uri(user.avatar.url)
            else:
                avatar_url = user.avatar.url
        
        return {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar': avatar_url,
        }

    def get_attachment_count(self, obj) -> int:
        return obj.attachments.count()

# apps/chat/serializers.py

# apps/chat/serializers.py

# apps/chat/serializers.py

class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear mensajes"""

    content = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Message
        fields = ['content']

    def validate(self, data):
        """
        Validación personalizada: permitir content vacío si hay archivo
        """
       
        content = data.get('content', '')
        
        if content is None:
            data['content'] = ''
        
        return data

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

class MessageUpdateSerializer(serializers.ModelSerializer):
    """
    Serializador para editar mensajes
    """

    class Meta:
        model = Message
        fields = ['content',]

    def update(self, instance, validated_data):

        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance

class AttachmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializador para crear adjuntos
    """

    class Meta:
        model = MessageAttachment
        fields = ['file', 'original_name', 'mime_type', 'size']

    def create(self, validated_data):
        validated_data['message_id'] = self.context.get('message_id')
        return super().create(validated_data)

        

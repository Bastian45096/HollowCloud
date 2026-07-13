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
            'status'
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

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
        messages = obj.messages.select_related('author').order_by('-created_at')[:50]
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
        
        try:
            membership = WorkspaceMember.objects.get(
                workspace=obj.channel.workspace,
                user=user
            )
            role = membership.role
        except WorkspaceMember.DoesNotExist:
            role = 'member'
        
        return {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar': avatar_url,
            'role': role,
        }

    def get_attachment_count(self, obj) -> int:
        return obj.attachments.count()


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear mensajes"""

    content = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Message
        fields = ['content']

    def validate(self, data):
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

class InviteMemberSerializer(serializers.Serializer):
    """
    Serializer para invitar a un miembro a un workspace.
    """
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(
        choices=WorkspaceMember.Role.choices,
        default=WorkspaceMember.Role.MEMBER,
        required=False
    )

    def validate_email(self, value):
        from apps.accounts.selectors import get_user_by_email
        try:
            user = get_user_by_email(email=value, use_cache=False)
            if not user:
                raise serializers.ValidationError("Usuario no encontrado")
        except:
            raise serializers.ValidationError("Usuario no encontrado")
        return value

    def validate(self, data):
        email = data.get('email')
        role = data.get('role', WorkspaceMember.Role.MEMBER) # <-- Se eliminó la importación local redundante
        workspace_id = self.context.get('workspace_id')
        user = self.context.get('user')
        
        from apps.accounts.selectors import get_user_by_email
        
        user_to_invite = get_user_by_email(email=email, use_cache=False)
        
        if not user_to_invite or not workspace_id:
            return data
        
        inviter_membership = WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=user
        ).first()
        
        if not inviter_membership:
            raise serializers.ValidationError("No eres miembro de este workspace")
        
        if role == WorkspaceMember.Role.ADMIN and inviter_membership.role != WorkspaceMember.Role.OWNER:
            raise serializers.ValidationError(
                "Solo el owner del workspace puede invitar como Administrador"
            )
        
        if WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=user_to_invite,
            status=WorkspaceMember.Status.ACTIVE
        ).exists():
            raise serializers.ValidationError(
                "El usuario ya es miembro de este workspace"
            )
        
        if WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=user_to_invite,
            status=WorkspaceMember.Status.PENDING
        ).exists():
            raise serializers.ValidationError(
                "El usuario ya posee una invitación pendiente a este workspace"
            )
        
        return data


class WorkspaceMemberResponseSerializer(serializers.ModelSerializer):
    """
    Serializer para FORMATEAR la respuesta de un miembro invitado.
    NO valida datos, solo los presenta.
    """
    
    user_id = serializers.UUIDField(source='user.id')
    username = serializers.CharField(source='user.username')
    email = serializers.EmailField(source='user.email')
    
    class Meta:
        model = WorkspaceMember
        fields = [
            'id',
            'user_id',
            'username',
            'email',
            'role',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LeaveWorkspaceResponseSerializer(serializers.Serializer):
    """
    Serializer para la respuesta de abandono de workspace.
    """
    success = serializers.BooleanField(help_text="Indica si la operación fue exitosa.")
    message = serializers.CharField(help_text="Mensaje descriptivo del resultado.")
    action_performed = serializers.BooleanField(
        help_text="True si se eliminó la membresía, False si ya no era miembro."
    )
    workspace_name = serializers.CharField(
        required=False, 
        help_text="Nombre del workspace abandonado (solo si action_performed es True)."
    )

class RevertAdminResponseSerializer(serializers.Serializer):
    """
    Contrato de respuesta para la reversión de Admin a Member.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    action_performed = serializers.BooleanField(
        help_text="Indica si se realizó un cambio real en la BD."
    )
    user_email = serializers.EmailField(required=False)
    workspace_name = serializers.CharField(required=False)
    old_role = serializers.CharField(required=False)
    new_role = serializers.CharField(required=False)
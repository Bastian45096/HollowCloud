# apps/api/urls.py

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.accounts.endpoints import LoginView, ProfileView, UpdateProfileView, LogoutView, RegisterView
from apps.chat.endpoints import (
    WorkspaceListCreateView,
    WorkspaceDetailView,
    WorkspaceMembersView,
    WorkspaceMemberRoleView,
    ChannelListCreateView,
    ChannelDetailView,
    MessageListCreateView,
    MessageDetailView,
    AttachmentUploadView,
    AttachmentDeleteView,
    WorkspaceSearchView,
    WorkspaceJoinView,
    CheckWorkspaceMembershipView,
    PromoverAdmin,
    RevertirAdmin,
    WorkspaceInviteView,
    AcceptInvitationView,
    RejectInvitationView,
    LeaveWorkspaceView,
)

from apps.notifications.endpoints import (
    NotificationListView,           # GET /api/notifications/
    NotificationMarkReadView,       # PATCH /api/notifications/mark-read/
    NotificationDetailView,         # GET /api/notifications/{uuid}/, DELETE /api/notifications/{uuid}/
    NotificationPreferenceView,     # GET /api/notifications/preferences/, PATCH /api/notifications/preferences/
    NotificationSummaryView,        # GET /api/notifications/summary/
    NotificationMarkSingleReadView, # PATCH /api/notifications/{uuid}/read/

)

from apps.storage.endpoints import (
    StorageContentView,
    CreateFolderView,
    UploadFileView,
    UpdateFileVersionView,
    ReplaceFileView,
)

urlpatterns = [
    # AUTH (JWT)
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),

    # ACCOUNTS API
    path("APIVIEWLG/", LoginView.as_view(), name="api-login"),
    path("APIVIEWPRF/", ProfileView.as_view(), name="api-profile"),
    path("APIVIEWUPDATEPRF/", UpdateProfileView.as_view(), name="api-profile-update"),
    path("APIVIEWLGT/", LogoutView.as_view(), name="api-logout"),
    path("APIVIEWCRTA/", RegisterView.as_view(), name="api-create-account"),

    # ============================================================
    # CHAT API (para que el JavaScript haga fetch)
    # ============================================================
    path("chat/workspaces/", WorkspaceListCreateView.as_view(), name="api-workspace-list-create"),
    path("chat/workspaces/<uuid:workspace_id>/", WorkspaceDetailView.as_view(), name="api-workspace-detail"),
    path("chat/workspaces/<uuid:workspace_id>/members/", WorkspaceMembersView.as_view(), name="api-workspace-members"),
    path("chat/workspaces/<uuid:workspace_id>/members/<uuid:user_id>/role/", WorkspaceMemberRoleView.as_view(), name="api-workspace-member-role"),
    path("chat/workspaces/<uuid:workspace_id>/channels/", ChannelListCreateView.as_view(), name="api-channel-list-create"),
    path("chat/workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/", ChannelDetailView.as_view(), name="api-channel-detail"),
    path("chat/workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/messages/", MessageListCreateView.as_view(), name="api-message-list-create"),
    path("chat/workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/messages/<uuid:message_id>/", MessageDetailView.as_view(), name="api-message-detail"),
    path("chat/workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/messages/<uuid:message_id>/attachments/", AttachmentUploadView.as_view(), name="api-attachment-upload"),
    path("chat/workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/messages/<uuid:message_id>/attachments/<uuid:attachment_id>/", AttachmentDeleteView.as_view(), name="api-attachment-delete"),
    path("chat/workspaces/search/", WorkspaceSearchView.as_view(), name="api-workspace-search"),
    path("chat/workspaces/<uuid:workspace_id>/join/", WorkspaceJoinView.as_view(), name="api-workspace-join"),
    path("chat/workspaces/<uuid:workspace_id>/promote-admin/", PromoverAdmin.as_view(), name="api-promover-admin"),
    path("chat/workspaces/<uuid:workspace_id>/revert-admin/", RevertirAdmin.as_view(), name="api-revertir-admin"),
    path("chat/workspaces/<uuid:workspace_id>/invite/", WorkspaceInviteView.as_view(), name="api-workspace-invite"),
    path('chat/invitations/<uuid:membership_id>/accept/', AcceptInvitationView.as_view(), name='accept-invitation'),
    path('chat/invitations/<uuid:membership_id>/reject/', RejectInvitationView.as_view(), name='reject-invitation'),
    path('chat/workspaces/<uuid:workspace_id>/leave/', LeaveWorkspaceView.as_view(), name='leave-workspace'),



    path('chat/workspaces/<uuid:workspace_id>/members/me/', CheckWorkspaceMembershipView.as_view(), name='check-membership'),
    
    #Notificaciones Api
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/<uuid:notification_id>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/preferences/', NotificationPreferenceView.as_view(), name='notification-preference'),
    path('notifications/summary/', NotificationSummaryView.as_view(), name='notification-summary'),
    path('notifications/<uuid:notification_id>/read/', NotificationMarkSingleReadView.as_view(), name='notification-mark-single-read'),   



    #Storage Api
    path('storage/<uuid:workspace_id>/items/', StorageContentView.as_view(), name='storage-content'),
    path('storage/<uuid:workspace_id>/folders/', CreateFolderView.as_view(), name='create-folder'),
    path('storage/<uuid:workspace_id>/upload/', UploadFileView.as_view(), name='upload-file'),
    path('storage/<uuid:workspace_id>/files/<uuid:file_id>/versions/', UpdateFileVersionView.as_view(), name='update-file-version'),
    path('storage/<uuid:workspace_id>/files/<uuid:file_id>/replace/', ReplaceFileView.as_view(), name='replace-file'),
]
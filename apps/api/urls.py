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
    CheckWorkspaceMembershipView
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






    path('chat/workspaces/<uuid:workspace_id>/members/me/', CheckWorkspaceMembershipView.as_view(), name='check-membership'),
]
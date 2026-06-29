# apps/chat/urls.py

from django.urls import path
from .web_views import (
    ChatDashboardView,
    WorkspaceView,
    ChannelView,
)

urlpatterns = [
    
    # Dashboard
    path('', ChatDashboardView.as_view(), name='chat_dashboard'),
    
    # Workspace views
    
    path('workspaces/<uuid:workspace_id>/', WorkspaceView.as_view(), name='chat_workspace'), 
    
    # Channel views
    
    path('workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/', ChannelView.as_view(), name='chat_channel'),
]
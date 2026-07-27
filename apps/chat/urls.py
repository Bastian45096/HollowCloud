# apps/chat/urls.py

from django.urls import path
from django.views.generic import RedirectView
from .web_views import (
    ChatDashboardView,
    WorkspaceView,
    ChannelView,
)

urlpatterns = [
    # Opción A: Redirigir /chat/ -> /chat/dashboard/ (Recomendado para evitar conflictos)
    path('', RedirectView.as_view(url='dashboard/', permanent=False)),
    
    # Opción B: El Dashboard ahora vive explícitamente en /chat/dashboard/
    path('dashboard/', ChatDashboardView.as_view(), name='chat_dashboard'),
    
    # Workspaces y Canales
    path('workspaces/<uuid:workspace_id>/', WorkspaceView.as_view(), name='chat_workspace'), 
    path('workspaces/<uuid:workspace_id>/channels/<uuid:channel_id>/', ChannelView.as_view(), name='chat_channel'),
]
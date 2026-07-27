from apps.storage.webviews import StorageWorkspaceView
from django.urls import path

urlpatterns = [
    path('<uuid:workspace_id>/', StorageWorkspaceView.as_view(), name='storage_workspace'),
]
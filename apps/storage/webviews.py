from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class StorageWorkspaceView(TemplateView):
    """
    Vista principal de Storage - Solo sirve el HTML.
    Toda la lógica de carpetas/archivos la hace el JS vía API Fetch.
    """
    template_name = 'storage_workspace.html'
    
    # Opcional: Si necesitas pasar solo el ID para que JS lo use inicialmente
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pasamos solo el ID desde la URL para que JS construya las rutas
        context['workspace_id'] = self.kwargs.get('workspace_id')
        return context
# apps/notifications/web_views.py

"""
Vistas web para la aplicación notifications.

Responsabilidades:
- Renderizar la página de notificaciones
- Servir el HTML base para el frontend
"""

from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class NotificationView(LoginRequiredMixin, View):
    """
    Vista principal de notificaciones.
    Renderiza el HTML con la lista de notificaciones del usuario.
    """
    template_name = 'notificaciones.html'

    def get(self, request):
        """
        Renderiza la página de notificaciones.
        """
        return render(request, self.template_name)
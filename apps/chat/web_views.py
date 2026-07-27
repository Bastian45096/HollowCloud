# apps/chat/web_views.py

from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class ChatDashboardView(View):
    """Vista principal del chat - solo sirve el HTML, todo lo demás lo hace JS"""
    template_name = 'chat/dashboard.html'

    def get(self, request):
        return render(request, self.template_name)


# ELIMINAR WorkspaceCreateView (ya no se usa)
# class WorkspaceCreateView(LoginRequiredMixin, View):
#     template_name = 'chat/workspace_form.html'
#     def get(self, request):
#         return render(request, self.template_name)


class WorkspaceView(View):
    """Vista de un workspace específico"""
    template_name = 'chat/dashboard.html'

    def get(self, request, workspace_id):
        return render(request, self.template_name, {'workspace_id': workspace_id})


# ELIMINAR ChannelCreateView (ya no se usa)
# class ChannelCreateView(LoginRequiredMixin, View):
#     template_name = 'chat/channel_form.html'
#     def get(self, request, workspace_id):
#         return render(request, self.template_name, {'workspace_id': workspace_id})


class ChannelView(View):
    """Vista de un canal específico"""
    template_name = 'chat/dashboard.html'

    def get(self, request, workspace_id, channel_id):
        return render(request, self.template_name, {
            'workspace_id': workspace_id,
            'channel_id': channel_id
        })
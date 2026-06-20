from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

class LoginPageView(TemplateView):
    template_name = "login.html"

class RegisterPageView(TemplateView):
    template_name = "register.html"

class DashboardPageView(
    TemplateView,
    LoginRequiredMixin
):
    template_name = "dashboard.html"

class ProfilePageView(
    TemplateView,
    LoginRequiredMixin
):
    template_name = "profile.html"

class LogoutView(TemplateView):
    template_name = "login.html"
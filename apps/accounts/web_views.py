from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

class LoginPageView(TemplateView):
    template_name = "accounts/login.html"

class RegisterPageView(TemplateView):
    template_name = "accounts/register.html"

class DashboardPageView(
    TemplateView,
    LoginRequiredMixin
):
    template_name = "accounts/dashboard.html"

class ProfilePageView(
    TemplateView,
    LoginRequiredMixin
):
    template_name = "accounts/profile.html"

class LogoutView(TemplateView):
    template_name = "accounts/login.html"
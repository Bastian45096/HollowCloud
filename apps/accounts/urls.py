from django.urls import path
from .web_views import(
    LoginPageView,
    DashboardPageView,
    ProfilePageView,
    LogoutView,
    RegisterPageView
)

urlpatterns = [
    path("login/", LoginPageView.as_view(), name="login"),
    path("accounts/dashboard/", DashboardPageView.as_view(), name="dashboard"),
    path("profile/", ProfilePageView.as_view(), name="profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterPageView.as_view(), name="register"),



]
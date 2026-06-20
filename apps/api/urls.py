from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.accounts.endpoints import LoginView, ProfileView, UpdateProfileView, LogoutView, RegisterView


urlpatterns = [
    # AUTH (JWT)
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),





    path("APIVIEWLG/", LoginView.as_view(), name="api-login"),
    path("APIVIEWPRF/", ProfileView.as_view(), name="api-profile"),
    path("APIVIEWUPDATEPRF/", UpdateProfileView.as_view(), name="api-profile-update"),
    path("APIVIEWLGT/", LogoutView.as_view(), name="api-logout"),
    path("APIVIEWCRTA/", RegisterView.as_view(), name="api-create-account"),

    # FUTURO: módulos del sistema
    # path("workspaces/", include("apps.chat.api.urls")),
    # path("storage/", include("apps.storage.api.urls")),
    # path("workflows/", include("apps.workflows.api.urls")),
]
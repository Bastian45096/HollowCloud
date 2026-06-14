from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # AUTH (JWT)
    path("auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="refresh"),

    # FUTURO: módulos del sistema
    # path("workspaces/", include("apps.chat.api.urls")),
    # path("storage/", include("apps.storage.api.urls")),
    # path("workflows/", include("apps.workflows.api.urls")),
]
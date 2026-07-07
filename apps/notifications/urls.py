# config/urls.py

from django.urls import path, include
from apps.notifications.web_views import NotificationView

urlpatterns = [
   
    path('', NotificationView.as_view(), name='notifications'),
]
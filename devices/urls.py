"""
URL patterns for devices app.
"""
from django.urls import path, re_path
from devices.views import root_health_view, DeviceListCreateView

urlpatterns = [
    path('', root_health_view, name='root-health'),
    re_path(r'^devices/?$', DeviceListCreateView.as_view(), name='device-list-create'),
]

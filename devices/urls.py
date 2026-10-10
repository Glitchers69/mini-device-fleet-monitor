"""
URL patterns for devices app.
"""
from django.urls import path, re_path
from devices.views import (
    root_health_view,
    DeviceListCreateView,
    DeviceHeartbeatView,
    DeviceDetailView,
    FleetSummaryView,
)

urlpatterns = [
    path('', root_health_view, name='root-health'),
    re_path(r'^devices/?$', DeviceListCreateView.as_view(), name='device-list-create'),
    re_path(r'^devices/(?P<pk>[^/]+)/heartbeat/?$', DeviceHeartbeatView.as_view(), name='device-heartbeat'),
    re_path(r'^devices/(?P<pk>[^/]+)/?$', DeviceDetailView.as_view(), name='device-detail'),
    re_path(r'^summary/?$', FleetSummaryView.as_view(), name='fleet-summary'),
]

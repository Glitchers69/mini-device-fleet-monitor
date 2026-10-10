"""
URL configuration for fleet_monitor project.
"""

from django.urls import path, include

urlpatterns = [
    path('', include('devices.urls')),
]

"""
URL patterns for devices app.
"""
from django.urls import path
from devices.views import root_health_view

urlpatterns = [
    path('', root_health_view, name='root-health'),
]

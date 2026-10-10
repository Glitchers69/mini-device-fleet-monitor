"""
Views for the devices app.
"""
from django.http import JsonResponse


def root_health_view(request):
    """Temporary root response confirming server is running."""
    return JsonResponse({"status": "running", "app": "fleet_monitor"})

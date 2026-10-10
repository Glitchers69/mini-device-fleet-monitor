"""
Views for the devices app.
"""
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from devices.models import Device
from devices.serializers import DeviceRegistrationSerializer


def root_health_view(request):
    """Root response confirming the application server is running."""
    return JsonResponse({"status": "running", "app": "fleet_monitor"})


class DeviceListCreateView(APIView):
    """
    POST /devices: Register a new device.
    Rejects missing fields with 400 Bad Request.
    Rejects duplicate IDs with 409 Conflict.
    Returns 201 Created on success.
    """

    def post(self, request, *args, **kwargs):
        # If payload is not a dictionary (e.g. invalid json format), reject as 400
        if not isinstance(request.data, dict):
            return Response(
                {"error": "Invalid request payload. Expected JSON object."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DeviceRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        device_id = serializer.validated_data['id']
        if Device.objects.filter(id=device_id).exists():
            return Response(
                {"error": f"Device with ID '{device_id}' already exists."},
                status=status.HTTP_409_CONFLICT
            )

        device = serializer.save()
        return Response(
            {"id": device.id, "name": device.name},
            status=status.HTTP_201_CREATED
        )

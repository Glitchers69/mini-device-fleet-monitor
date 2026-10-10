"""
Views for the devices app.
"""
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from devices.models import Device
from devices.serializers import (
    DeviceRegistrationSerializer,
    HeartbeatSerializer,
    DeviceReadSerializer,
)
from devices.utils import compute_status


def root_health_view(request):
    """Root response confirming the application server is running."""
    return JsonResponse({"status": "running", "app": "fleet_monitor"})


class DeviceListCreateView(APIView):
    """
    GET /devices: List all registered devices with dynamically computed status (FR-4).
    POST /devices: Register a new device (FR-1).
    """

    def get(self, request, *args, **kwargs):
        devices = Device.objects.all()
        now = timezone.now()
        serializer = DeviceReadSerializer(devices, many=True, context={'now': now})
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class DeviceHeartbeatView(APIView):
    """
    POST /devices/{id}/heartbeat: Record a device heartbeat (FR-2).
    Returns 200 OK on success with server-side received timestamp recorded.
    Returns 404 Not Found if device is unknown.
    Returns 400 Bad Request on invalid payload or missing fields.
    """

    def post(self, request, pk=None, *args, **kwargs):
        if not isinstance(request.data, dict):
            return Response(
                {"error": "Invalid request payload. Expected JSON object."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            device = Device.objects.get(id=pk)
        except Device.DoesNotExist:
            return Response(
                {"error": "Device not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = HeartbeatSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        device.last_heartbeat = now
        device.last_client_timestamp = serializer.validated_data['timestamp']
        device.last_status = serializer.validated_data['status']
        device.save(update_fields=['last_heartbeat', 'last_client_timestamp', 'last_status'])

        return Response({"status": "OK"}, status=status.HTTP_200_OK)


class DeviceDetailView(APIView):
    """
    GET /devices/{id}: Retrieve single device record with dynamically computed status (FR-5).
    Returns 200 OK with id, name, status, and last_heartbeat.
    Returns 404 Not Found if device does not exist.
    """

    def get(self, request, pk=None, *args, **kwargs):
        try:
            device = Device.objects.get(id=pk)
        except Device.DoesNotExist:
            return Response(
                {"error": "Device not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        now = timezone.now()
        serializer = DeviceReadSerializer(device, context={'now': now})
        return Response(serializer.data, status=status.HTTP_200_OK)


class FleetSummaryView(APIView):
    """
    GET /summary: Retrieve fleet health summary (FR-6).
    Returns {"total": N, "online": M, "offline": N - M} computed at request time.
    """

    def get(self, request, *args, **kwargs):
        devices = Device.objects.all()
        now = timezone.now()
        total = len(devices)
        online = sum(1 for d in devices if compute_status(d.last_heartbeat, now=now) == "ONLINE")
        offline = total - online
        return Response(
            {
                "total": total,
                "online": online,
                "offline": offline,
            },
            status=status.HTTP_200_OK
        )

"""
Serializers for the devices app.
"""
from rest_framework import serializers
from devices.models import Device
from devices.utils import compute_status


class DeviceRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new device via POST /devices.
    """
    id = serializers.CharField(
        max_length=64,
        required=True,
        allow_blank=False,
        trim_whitespace=True
    )
    name = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
        trim_whitespace=True
    )

    class Meta:
        model = Device
        fields = ['id', 'name']
        extra_kwargs = {
            # Unique validation is handled explicitly in the view to return HTTP 409 Conflict per FR-1
            'id': {'validators': []}
        }

    def validate_id(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Device ID cannot be empty.")
        return cleaned

    def validate_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Device name cannot be empty.")
        return cleaned


class HeartbeatSerializer(serializers.Serializer):
    """
    Serializer for validating device heartbeat payloads via POST /devices/{id}/heartbeat.
    """
    timestamp = serializers.DateTimeField(required=True)
    status = serializers.CharField(
        max_length=10,
        required=True,
        allow_blank=False,
        trim_whitespace=True
    )

    def validate_status(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Status cannot be empty.")
        return cleaned


class DeviceReadSerializer(serializers.ModelSerializer):
    """
    Serializer for reading device records (GET /devices and GET /devices/{id}).
    Computes status dynamically at request time (AD-2, FR-3, FR-4).
    """
    status = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ['id', 'name', 'status', 'last_heartbeat']

    def get_status(self, obj):
        now = self.context.get('now') if self.context else None
        return compute_status(obj.last_heartbeat, now=now)

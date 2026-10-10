"""
Serializers for the devices app.
"""
from rest_framework import serializers
from devices.models import Device


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

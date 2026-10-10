"""
Tests for Device Registration (FR-1: POST /devices).
"""
import json
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from devices.models import Device


class DeviceRegistrationTests(TestCase):
    """
    Automated test coverage for device registration endpoint.
    """

    def setUp(self):
        self.client = APIClient()

    def test_register_device_success(self):
        """Valid registration returns 201 Created and persists the Device."""
        payload = {"id": "device-01", "name": "Lab Device 01"}
        response = self.client.post("/devices", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"id": "device-01", "name": "Lab Device 01"})

        # Verify DB persistence
        device = Device.objects.get(id="device-01")
        self.assertEqual(device.name, "Lab Device 01")

    def test_register_device_trailing_slash(self):
        """Valid registration with trailing slash /devices/ returns 201 Created."""
        payload = {"id": "device-02", "name": "Lab Device 02"}
        response = self.client.post("/devices/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Device.objects.filter(id="device-02").exists())

    def test_register_device_duplicate_rejected(self):
        """Duplicate registration with existing ID returns 409 Conflict."""
        # Pre-create device
        Device.objects.create(id="device-01", name="Lab Device 01")

        payload = {"id": "device-01", "name": "Duplicate Attempt"}
        response = self.client.post("/devices", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("error", response.data)

    def test_register_device_missing_id(self):
        """Registration without 'id' returns 400 Bad Request."""
        payload = {"name": "Device Without ID"}
        response = self.client.post("/devices", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id", response.data)

    def test_register_device_missing_name(self):
        """Registration without 'name' returns 400 Bad Request."""
        payload = {"id": "device-03"}
        response = self.client.post("/devices", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_register_device_blank_id(self):
        """Registration with blank/empty 'id' returns 400 Bad Request."""
        payload = {"id": "   ", "name": "Blank ID Device"}
        response = self.client.post("/devices", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_device_blank_name(self):
        """Registration with blank/empty 'name' returns 400 Bad Request."""
        payload = {"id": "device-04", "name": "   "}
        response = self.client.post("/devices", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registered_device_initial_state(self):
        """Newly registered device starts with last_heartbeat = None."""
        payload = {"id": "device-initial", "name": "Initial Device"}
        response = self.client.post("/devices", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(id="device-initial")
        self.assertIsNone(device.last_heartbeat)
        self.assertIsNone(device.last_client_timestamp)
        self.assertIsNone(device.last_status)

    def test_register_device_invalid_payload_format(self):
        """Non-dictionary JSON payload returns 400 Bad Request."""
        response = self.client.post(
            "/devices",
            data=json.dumps(["invalid", "list"]),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

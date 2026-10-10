"""
Tests for Heartbeat Handling (FR-2: POST /devices/{id}/heartbeat).
"""
import json
from datetime import timedelta
from unittest import mock
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from devices.models import Device


class DeviceHeartbeatTests(TestCase):
    """
    Automated test coverage for device heartbeat endpoint.
    All timing is controlled via mocked timezone.now (zero time.sleep per NFR-4).
    """

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(id="device-01", name="Lab Device 01")

    def test_heartbeat_success(self):
        """Valid heartbeat returns 200 OK and updates server-side timestamp and client fields."""
        client_ts = "2026-09-21T10:30:00Z"
        payload = {"timestamp": client_ts, "status": "OK"}

        fixed_server_now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=fixed_server_now):
            response = self.client.post(
                f"/devices/{self.device.id}/heartbeat",
                payload,
                format="json"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "OK"})

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_heartbeat, fixed_server_now)
        self.assertEqual(self.device.last_client_timestamp.isoformat(), "2026-09-21T10:30:00+00:00")
        self.assertEqual(self.device.last_status, "OK")

    def test_heartbeat_trailing_slash(self):
        """Heartbeat endpoint with trailing slash returns 200 OK."""
        payload = {"timestamp": "2026-09-21T10:30:00Z", "status": "OK"}
        response = self.client.post(f"/devices/{self.device.id}/heartbeat/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_heartbeat_unregistered_device(self):
        """Heartbeat to an unregistered device returns 404 Not Found."""
        payload = {"timestamp": "2026-09-21T10:30:00Z", "status": "OK"}
        response = self.client.post("/devices/device-unknown/heartbeat", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"error": "Device not found."})

    def test_heartbeat_missing_status(self):
        """Heartbeat without 'status' returns 400 Bad Request."""
        payload = {"timestamp": "2026-09-21T10:30:00Z"}
        response = self.client.post(f"/devices/{self.device.id}/heartbeat", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_heartbeat_blank_status(self):
        """Heartbeat with empty/whitespace 'status' returns 400 Bad Request."""
        payload = {"timestamp": "2026-09-21T10:30:00Z", "status": "   "}
        response = self.client.post(f"/devices/{self.device.id}/heartbeat", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_heartbeat_missing_timestamp(self):
        """Heartbeat without 'timestamp' returns 400 Bad Request."""
        payload = {"status": "OK"}
        response = self.client.post(f"/devices/{self.device.id}/heartbeat", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timestamp", response.data)

    def test_heartbeat_invalid_timestamp_format(self):
        """Heartbeat with non-ISO timestamp returns 400 Bad Request."""
        payload = {"timestamp": "invalid-datetime-string", "status": "OK"}
        response = self.client.post(f"/devices/{self.device.id}/heartbeat", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timestamp", response.data)

    def test_heartbeat_overwrites_previous(self):
        """Subsequent heartbeats overwrite last_heartbeat with the newer server timestamp."""
        t1 = timezone.now()
        t2 = t1 + timedelta(seconds=10)

        with mock.patch("django.utils.timezone.now", return_value=t1):
            r1 = self.client.post(
                f"/devices/{self.device.id}/heartbeat",
                {"timestamp": "2026-09-21T10:30:00Z", "status": "OK"},
                format="json"
            )
            self.assertEqual(r1.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_heartbeat, t1)

        with mock.patch("django.utils.timezone.now", return_value=t2):
            r2 = self.client.post(
                f"/devices/{self.device.id}/heartbeat",
                {"timestamp": "2026-09-21T10:30:10Z", "status": "BUSY"},
                format="json"
            )
            self.assertEqual(r2.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        self.assertEqual(self.device.last_heartbeat, t2)
        self.assertEqual(self.device.last_status, "BUSY")

    def test_heartbeat_server_time_used(self):
        """Server-side received timestamp is recorded independently of client clock drift."""
        client_drifted_ts = "2020-01-01T00:00:00Z"  # Client clock is 6 years in the past
        fixed_server_now = timezone.now()

        with mock.patch("django.utils.timezone.now", return_value=fixed_server_now):
            response = self.client.post(
                f"/devices/{self.device.id}/heartbeat",
                {"timestamp": client_drifted_ts, "status": "OK"},
                format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.device.refresh_from_db()
        # Server recorded current server time, NOT the client's drifted 2020 timestamp
        self.assertEqual(self.device.last_heartbeat, fixed_server_now)
        self.assertNotEqual(self.device.last_heartbeat.year, 2020)
        self.assertEqual(self.device.last_client_timestamp.year, 2020)

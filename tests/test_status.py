"""
Tests for Status Computation and Read Endpoints (FR-3, FR-4, FR-5, FR-6).
"""
from datetime import timedelta
from unittest import mock
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from devices.models import Device
from devices.utils import compute_status
from devices.constants import ONLINE_THRESHOLD_SECONDS


class StatusComputationUnitTests(TestCase):
    """
    Unit tests for the compute_status utility function.
    """

    def test_compute_status_none_is_offline(self):
        """None last_heartbeat returns 'OFFLINE'."""
        self.assertEqual(compute_status(None), "OFFLINE")

    def test_compute_status_recent_heartbeat_is_online(self):
        """Heartbeat 29 seconds in the past is 'ONLINE'."""
        fixed_now = timezone.now()
        hb = fixed_now - timedelta(seconds=29)
        self.assertEqual(compute_status(hb, now=fixed_now), "ONLINE")

    def test_compute_status_expired_heartbeat_is_offline(self):
        """Heartbeat 31 seconds in the past is 'OFFLINE'."""
        fixed_now = timezone.now()
        hb = fixed_now - timedelta(seconds=31)
        self.assertEqual(compute_status(hb, now=fixed_now), "OFFLINE")

    def test_compute_status_default_now(self):
        """compute_status uses timezone.now() when 'now' parameter is omitted."""
        fixed_now = timezone.now()
        hb = fixed_now - timedelta(seconds=10)
        with mock.patch("django.utils.timezone.now", return_value=fixed_now):
            self.assertEqual(compute_status(hb), "ONLINE")


class StatusReadEndpointsIntegrationTests(TestCase):
    """
    Integration tests for GET /devices, GET /devices/{id}, and GET /summary.
    """

    def setUp(self):
        self.client = APIClient()

    def test_get_devices_list_status_evaluation(self):
        """GET /devices returns computed status for each device."""
        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            Device.objects.create(id="dev-active", name="Active Device", last_heartbeat=now - timedelta(seconds=10))
            Device.objects.create(id="dev-expired", name="Expired Device", last_heartbeat=now - timedelta(seconds=40))
            Device.objects.create(id="dev-never", name="Never Device", last_heartbeat=None)

            response = self.client.get("/devices")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        devices_data = {d["id"]: d for d in response.data}

        self.assertEqual(devices_data["dev-active"]["status"], "ONLINE")
        self.assertIsNotNone(devices_data["dev-active"]["last_heartbeat"])

        self.assertEqual(devices_data["dev-expired"]["status"], "OFFLINE")
        self.assertIsNotNone(devices_data["dev-expired"]["last_heartbeat"])

        self.assertEqual(devices_data["dev-never"]["status"], "OFFLINE")
        self.assertIsNone(devices_data["dev-never"]["last_heartbeat"])

    def test_get_device_detail_newly_registered(self):
        """GET /devices/{id} on newly registered device has status 'OFFLINE' and last_heartbeat null."""
        dev = Device.objects.create(id="dev-new", name="New Device")
        response = self.client.get(f"/devices/{dev.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], "dev-new")
        self.assertEqual(response.data["name"], "New Device")
        self.assertEqual(response.data["status"], "OFFLINE")
        self.assertIsNone(response.data["last_heartbeat"])

    def test_get_device_detail_online(self):
        """GET /devices/{id} with recent heartbeat has status 'ONLINE'."""
        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            dev = Device.objects.create(
                id="dev-online",
                name="Online Device",
                last_heartbeat=now - timedelta(seconds=15)
            )
            response = self.client.get(f"/devices/{dev.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ONLINE")
        self.assertIsNotNone(response.data["last_heartbeat"])

    def test_get_device_detail_offline_after_timeout(self):
        """GET /devices/{id} with heartbeat > 30s ago has status 'OFFLINE'."""
        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            dev = Device.objects.create(
                id="dev-stale",
                name="Stale Device",
                last_heartbeat=now - timedelta(seconds=35)
            )
            response = self.client.get(f"/devices/{dev.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "OFFLINE")

    def test_get_summary_fleet_counts(self):
        """GET /summary correctly counts total, online, and offline devices dynamically."""
        now = timezone.now()
        with mock.patch("django.utils.timezone.now", return_value=now):
            Device.objects.create(id="d1", name="Dev 1", last_heartbeat=now - timedelta(seconds=5))
            Device.objects.create(id="d2", name="Dev 2", last_heartbeat=now - timedelta(seconds=15))
            Device.objects.create(id="d3", name="Dev 3", last_heartbeat=now - timedelta(seconds=50))
            Device.objects.create(id="d4", name="Dev 4", last_heartbeat=None)

            response = self.client.get("/summary")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 4)
        self.assertEqual(response.data["online"], 2)
        self.assertEqual(response.data["offline"], 2)
        self.assertEqual(response.data["total"], response.data["online"] + response.data["offline"])

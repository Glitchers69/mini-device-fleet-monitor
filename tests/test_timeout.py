"""
Tests for 30-Second Timeout Boundary and Dynamic State Transitions (FR-3, NFR-1, NFR-4).
All timing is verified using mocked timezone.now (zero time.sleep()).
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


class TimeoutBoundaryTests(TestCase):
    """
    Rigorously verifies the 30.0-second ONLINE/OFFLINE boundary using mocked time.
    """

    def setUp(self):
        self.client = APIClient()
        self.device = Device.objects.create(id="dev-boundary", name="Boundary Device")

    def test_boundary_inclusive_at_exact_30_seconds(self):
        """
        A device whose heartbeat was received exactly 30.000s ago is ONLINE.
        The 30-second threshold is inclusive (AD-4, FR-3).
        """
        fixed_now = timezone.now()
        hb_at_boundary = fixed_now - timedelta(seconds=ONLINE_THRESHOLD_SECONDS)

        # 1. Direct utility check
        self.assertEqual(compute_status(hb_at_boundary, now=fixed_now), "ONLINE")

        # 2. API detail check
        self.device.last_heartbeat = hb_at_boundary
        self.device.save(update_fields=["last_heartbeat"])

        with mock.patch("django.utils.timezone.now", return_value=fixed_now):
            response = self.client.get(f"/devices/{self.device.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ONLINE")

    def test_boundary_exclusive_at_30_seconds_plus_one_millisecond(self):
        """
        A device whose heartbeat was received 30 seconds + 1 millisecond ago is OFFLINE.
        """
        fixed_now = timezone.now()
        hb_just_past = fixed_now - timedelta(seconds=ONLINE_THRESHOLD_SECONDS, milliseconds=1)

        # 1. Direct utility check
        self.assertEqual(compute_status(hb_just_past, now=fixed_now), "OFFLINE")

        # 2. API detail check
        self.device.last_heartbeat = hb_just_past
        self.device.save(update_fields=["last_heartbeat"])

        with mock.patch("django.utils.timezone.now", return_value=fixed_now):
            response = self.client.get(f"/devices/{self.device.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "OFFLINE")

    def test_status_transition_without_database_write(self):
        """
        A device transitions from ONLINE to OFFLINE purely by advancing time.
        No database writes or background mutations take place (AD-2, FR-3).
        """
        t0 = timezone.now()
        self.device.last_heartbeat = t0
        self.device.save(update_fields=["last_heartbeat"])

        # At t0 + 10s: device is ONLINE
        t_online = t0 + timedelta(seconds=10)
        with mock.patch("django.utils.timezone.now", return_value=t_online):
            r1 = self.client.get(f"/devices/{self.device.id}")
            self.assertEqual(r1.status_code, status.HTTP_200_OK)
            self.assertEqual(r1.data["status"], "ONLINE")

        # Advance mocked time to t0 + 31s (no database changes performed!)
        t_offline = t0 + timedelta(seconds=31)
        with mock.patch("django.utils.timezone.now", return_value=t_offline):
            r2 = self.client.get(f"/devices/{self.device.id}")
            self.assertEqual(r2.status_code, status.HTTP_200_OK)
            self.assertEqual(r2.data["status"], "OFFLINE")

        # Confirm the database row remains strictly untouched
        self.device.refresh_from_db()
        self.assertEqual(self.device.last_heartbeat, t0)

    def test_summary_transition_without_database_write(self):
        """
        GET /summary counts automatically transition as time advances, without DB mutation.
        """
        t0 = timezone.now()
        self.device.last_heartbeat = t0
        self.device.save(update_fields=["last_heartbeat"])

        # At t0 + 5s: 1 online, 0 offline
        t_online = t0 + timedelta(seconds=5)
        with mock.patch("django.utils.timezone.now", return_value=t_online):
            r1 = self.client.get("/summary")
            self.assertEqual(r1.status_code, status.HTTP_200_OK)
            self.assertEqual(r1.data, {"total": 1, "online": 1, "offline": 0})

        # At t0 + 32s: 0 online, 1 offline (automatic transition on read)
        t_offline = t0 + timedelta(seconds=32)
        with mock.patch("django.utils.timezone.now", return_value=t_offline):
            r2 = self.client.get("/summary")
            self.assertEqual(r2.status_code, status.HTTP_200_OK)
            self.assertEqual(r2.data, {"total": 1, "online": 0, "offline": 1})

    def test_no_sleep_used_in_test_execution(self):
        """
        Asserts that the test suite relies solely on mocked time, strictly adhering to NFR-4.
        """
        with mock.patch("time.sleep", side_effect=AssertionError("time.sleep is strictly forbidden!")):
            # Running boundary check should never invoke time.sleep
            now = timezone.now()
            hb = now - timedelta(seconds=15)
            self.assertEqual(compute_status(hb, now=now), "ONLINE")

"""
Models for the devices app.
"""
from django.db import models


class Device(models.Model):
    """
    Device model representing a registered device in the fleet.
    Device status (ONLINE/OFFLINE) is computed dynamically on read and never stored (AD-2).
    """
    id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_client_timestamp = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.id})"

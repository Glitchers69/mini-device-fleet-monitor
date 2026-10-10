"""
Utility functions for the devices app.
"""
from datetime import datetime
from django.utils import timezone
from devices.constants import ONLINE_THRESHOLD_SECONDS


def compute_status(last_heartbeat: datetime | None, now: datetime | None = None) -> str:
    """
    Computes a device's status ('ONLINE' or 'OFFLINE') based on its last heartbeat.

    Rules:
    - If last_heartbeat is None (never received a heartbeat), returns 'OFFLINE'.
    - If now is None, defaults to django.utils.timezone.now().
    - If elapsed time between now and last_heartbeat is within ONLINE_THRESHOLD_SECONDS (inclusive, <= 30.0s)
      and >= 0s (with small tolerance for sub-millisecond clock drift), returns 'ONLINE'.
    - Otherwise (elapsed > 30s), returns 'OFFLINE'.
    """
    if last_heartbeat is None:
        return "OFFLINE"

    if now is None:
        now = timezone.now()

    # Ensure timezone awareness consistency between operands
    if timezone.is_aware(last_heartbeat) and timezone.is_naive(now):
        now = timezone.make_aware(now, timezone.get_current_timezone())
    elif timezone.is_naive(last_heartbeat) and timezone.is_aware(now):
        last_heartbeat = timezone.make_aware(last_heartbeat, timezone.get_current_timezone())

    elapsed_seconds = (now - last_heartbeat).total_seconds()

    if -1.0 <= elapsed_seconds <= ONLINE_THRESHOLD_SECONDS:
        return "ONLINE"

    return "OFFLINE"

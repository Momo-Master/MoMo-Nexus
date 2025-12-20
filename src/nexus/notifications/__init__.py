"""
Notification System.

Provides push notifications via Ntfy.sh and other services.
"""

from nexus.notifications.ntfy import NtfyClient, NtfyConfig
from nexus.notifications.manager import NotificationManager

__all__ = [
    "NtfyClient",
    "NtfyConfig",
    "NotificationManager",
]


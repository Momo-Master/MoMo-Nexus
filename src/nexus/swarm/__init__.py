"""
MoMo-Swarm Integration for Nexus.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Off-grid C2 & LoRa mesh network functionality integrated into Nexus.
Provides encrypted mesh communication with field devices.

Original: MoMo-Swarm standalone project
Merged into: MoMo-Nexus v1.1.0

:copyright: (c) 2025 MoMo Team
:license: MIT
"""

from nexus.swarm.bridge import BridgeStats, SwarmBridge, SwarmConfig
from nexus.swarm.manager import SwarmManager
from nexus.swarm.notifications import (
    NotificationBuilder,
    NotifyIcon,
    OperatorNotification,
    notifications,
    notify_alert,
    notify_cracked,
    notify_handshake,
    notify_status,
)
from nexus.swarm.protocol import (
    AckStatus,
    CommandCode,
    EventCode,
    SequenceTracker,
    SwarmMessage,
    SwarmMessageBuilder,
    SwarmMessageType,
)

__all__ = [
    # Protocol
    "SwarmMessage",
    "SwarmMessageType",
    "EventCode",
    "CommandCode",
    "AckStatus",
    "SwarmMessageBuilder",
    "SequenceTracker",
    # Bridge
    "SwarmBridge",
    "SwarmConfig",
    "BridgeStats",
    # Manager
    "SwarmManager",
    # Notifications
    "OperatorNotification",
    "NotificationBuilder",
    "NotifyIcon",
    "notifications",
    "notify_handshake",
    "notify_cracked",
    "notify_status",
    "notify_alert",
]


"""
Alert System.

Manages alerts, notifications, and severity tracking.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

from nexus.core.events import EventBus, EventType, get_event_bus
from nexus.domain.models import Message, generate_id

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"  # Immediate attention required
    HIGH = "high"  # Important, should be addressed soon
    MEDIUM = "medium"  # Notable event
    LOW = "low"  # Informational
    INFO = "info"  # Debug/trace level


class AlertType(str, Enum):
    """Types of alerts."""

    # Device alerts
    DEVICE_OFFLINE = "device_offline"
    DEVICE_LOST = "device_lost"
    DEVICE_LOW_BATTERY = "device_low_battery"
    DEVICE_ERROR = "device_error"

    # Channel alerts
    CHANNEL_DOWN = "channel_down"
    CHANNEL_DEGRADED = "channel_degraded"

    # Security alerts
    HANDSHAKE_CAPTURED = "handshake_captured"
    PASSWORD_CRACKED = "password_cracked"
    CREDENTIAL_CAPTURED = "credential_captured"
    EVIL_TWIN_CLIENT = "evil_twin_client"

    # System alerts
    SYSTEM_ERROR = "system_error"
    QUEUE_FULL = "queue_full"

    # Custom
    CUSTOM = "custom"


@dataclass
class Alert:
    """Alert data structure."""

    id: str = field(default_factory=generate_id)
    type: AlertType = AlertType.CUSTOM
    severity: AlertSeverity = AlertSeverity.MEDIUM
    title: str = ""
    message: str = ""
    source: str = "nexus"
    device_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None


# Type alias for alert handlers
AlertHandler = Callable[[Alert], Coroutine[Any, Any, None]]


class AlertManager:
    """
    Manages alerts and notifications.

    Responsibilities:
    - Create and store alerts
    - Notify handlers (webhooks, push, etc.)
    - Track acknowledgments
    - Provide alert queries
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        max_alerts: int = 10000,
    ) -> None:
        self._event_bus = event_bus or get_event_bus()
        self._max_alerts = max_alerts

        # Alert storage
        self._alerts: list[Alert] = []
        self._alerts_by_id: dict[str, Alert] = {}
        self._lock = asyncio.Lock()

        # Handlers
        self._handlers: list[AlertHandler] = []

        # Severity counts
        self._severity_counts: dict[AlertSeverity, int] = {s: 0 for s in AlertSeverity}

    # =========================================================================
    # Alert Creation
    # =========================================================================

    async def create(
        self,
        type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str = "",
        source: str = "nexus",
        device_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> Alert:
        """
        Create a new alert.

        Args:
            type: Alert type
            severity: Severity level
            title: Short title
            message: Detailed message
            source: Alert source
            device_id: Related device
            data: Additional data

        Returns:
            Created alert
        """
        alert = Alert(
            type=type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            device_id=device_id,
            data=data or {},
        )

        await self._store_alert(alert)
        await self._notify_handlers(alert)

        # Emit event
        await self._event_bus.emit(
            EventType.ALERT_NEW,
            {
                "alert_id": alert.id,
                "type": type.value,
                "severity": severity.value,
                "title": title,
                "device_id": device_id,
            },
        )

        logger.info(f"Alert created: [{severity.value.upper()}] {title}")

        return alert

    async def create_from_message(self, message: Message) -> Alert:
        """
        Create alert from incoming ALERT message.

        Args:
            message: Alert message from device

        Returns:
            Created alert
        """
        data = message.data

        # Determine alert type
        alert_type_str = data.get("type", "custom")
        try:
            alert_type = AlertType(alert_type_str)
        except ValueError:
            alert_type = AlertType.CUSTOM

        # Determine severity
        severity_str = data.get("severity", "medium")
        try:
            severity = AlertSeverity(severity_str)
        except ValueError:
            severity = AlertSeverity.MEDIUM

        return await self.create(
            type=alert_type,
            severity=severity,
            title=data.get("title", alert_type_str),
            message=data.get("message", ""),
            source=message.src,
            device_id=message.src,
            data=data.get("data", data),
        )

    async def _store_alert(self, alert: Alert) -> None:
        """Store alert in memory."""
        async with self._lock:
            self._alerts.append(alert)
            self._alerts_by_id[alert.id] = alert
            self._severity_counts[alert.severity] += 1

            # Trim if over limit
            while len(self._alerts) > self._max_alerts:
                old = self._alerts.pop(0)
                self._alerts_by_id.pop(old.id, None)
                self._severity_counts[old.severity] -= 1

    # =========================================================================
    # Handlers
    # =========================================================================

    def add_handler(self, handler: AlertHandler) -> None:
        """Add alert handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: AlertHandler) -> None:
        """Remove alert handler."""
        try:
            self._handlers.remove(handler)
        except ValueError:
            pass

    async def _notify_handlers(self, alert: Alert) -> None:
        """Notify all handlers of new alert."""
        for handler in self._handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    # =========================================================================
    # Acknowledgment
    # =========================================================================

    async def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: str = "operator",
    ) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            acknowledged_by: Who acknowledged

        Returns:
            True if acknowledged
        """
        async with self._lock:
            alert = self._alerts_by_id.get(alert_id)
            if not alert:
                return False

            alert.acknowledged = True
            alert.acknowledged_at = datetime.now()
            alert.acknowledged_by = acknowledged_by

        await self._event_bus.emit(
            EventType.ALERT_ACKED,
            {"alert_id": alert_id, "by": acknowledged_by},
        )

        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True

    async def acknowledge_all(
        self,
        device_id: str | None = None,
        severity: AlertSeverity | None = None,
        acknowledged_by: str = "operator",
    ) -> int:
        """
        Acknowledge multiple alerts.

        Args:
            device_id: Filter by device
            severity: Filter by severity
            acknowledged_by: Who acknowledged

        Returns:
            Number of alerts acknowledged
        """
        count = 0

        async with self._lock:
            for alert in self._alerts:
                if alert.acknowledged:
                    continue

                if device_id and alert.device_id != device_id:
                    continue

                if severity and alert.severity != severity:
                    continue

                alert.acknowledged = True
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                count += 1

        logger.info(f"Acknowledged {count} alerts by {acknowledged_by}")
        return count

    # =========================================================================
    # Queries
    # =========================================================================

    async def get(self, alert_id: str) -> Alert | None:
        """Get alert by ID."""
        async with self._lock:
            return self._alerts_by_id.get(alert_id)

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        unacknowledged_only: bool = False,
        severity: AlertSeverity | None = None,
        device_id: str | None = None,
        alert_type: AlertType | None = None,
    ) -> list[Alert]:
        """
        Get alerts with filters.

        Args:
            limit: Max alerts to return
            offset: Offset for pagination
            unacknowledged_only: Only unacknowledged
            severity: Filter by severity
            device_id: Filter by device
            alert_type: Filter by type

        Returns:
            List of matching alerts
        """
        async with self._lock:
            alerts = list(reversed(self._alerts))  # Newest first

        # Apply filters
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if device_id:
            alerts = [a for a in alerts if a.device_id == device_id]

        if alert_type:
            alerts = [a for a in alerts if a.type == alert_type]

        # Apply pagination
        return alerts[offset : offset + limit]

    async def get_recent(self, count: int = 10) -> list[Alert]:
        """Get most recent alerts."""
        return await self.get_all(limit=count)

    async def get_unacknowledged(self) -> list[Alert]:
        """Get all unacknowledged alerts."""
        return await self.get_all(unacknowledged_only=True, limit=self._max_alerts)

    async def get_by_severity(self, severity: AlertSeverity) -> list[Alert]:
        """Get alerts by severity."""
        return await self.get_all(severity=severity, limit=self._max_alerts)

    async def get_critical(self) -> list[Alert]:
        """Get critical unacknowledged alerts."""
        async with self._lock:
            return [
                a for a in self._alerts
                if a.severity == AlertSeverity.CRITICAL and not a.acknowledged
            ]

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get alert statistics."""
        async with self._lock:
            alerts = list(self._alerts)

        unacked = sum(1 for a in alerts if not a.acknowledged)

        return {
            "total": len(alerts),
            "unacknowledged": unacked,
            "by_severity": dict(self._severity_counts),
            "by_type": {
                t.value: sum(1 for a in alerts if a.type == t)
                for t in AlertType
                if sum(1 for a in alerts if a.type == t) > 0
            },
            "critical_unacked": sum(
                1 for a in alerts
                if a.severity == AlertSeverity.CRITICAL and not a.acknowledged
            ),
        }

    async def count(self) -> int:
        """Get total alert count."""
        async with self._lock:
            return len(self._alerts)

    async def clear_old(self, days: int = 30) -> int:
        """Clear alerts older than N days."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        count = 0

        async with self._lock:
            new_alerts = []
            for alert in self._alerts:
                if alert.timestamp >= cutoff:
                    new_alerts.append(alert)
                else:
                    self._alerts_by_id.pop(alert.id, None)
                    self._severity_counts[alert.severity] -= 1
                    count += 1

            self._alerts = new_alerts

        logger.info(f"Cleared {count} old alerts")
        return count


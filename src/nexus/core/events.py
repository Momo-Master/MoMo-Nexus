"""
Event bus for internal communication.

Pub/Sub pattern for loose coupling between components.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types in the system."""

    # Message events
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    MESSAGE_QUEUED = "message.queued"
    MESSAGE_FAILED = "message.failed"
    MESSAGE_ACKED = "message.acked"

    # Device events
    DEVICE_REGISTERED = "device.registered"
    DEVICE_ONLINE = "device.online"
    DEVICE_OFFLINE = "device.offline"
    DEVICE_LOST = "device.lost"
    DEVICE_STATUS = "device.status"

    # Channel events
    CHANNEL_UP = "channel.up"
    CHANNEL_DOWN = "channel.down"
    CHANNEL_DEGRADED = "channel.degraded"

    # Alert events
    ALERT_NEW = "alert.new"
    ALERT_ACKED = "alert.acked"

    # Zone events
    ZONE_ENTER = "zone.enter"
    ZONE_EXIT = "zone.exit"
    ZONE_DWELL = "zone.dwell"

    # Channel registry
    CHANNEL_REGISTERED = "channel.registered"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"


@dataclass
class Event:
    """Event data container."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "nexus"
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if isinstance(self.type, str):
            self.type = EventType(self.type)


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async event bus for internal communication.

    Supports pub/sub pattern with async handlers.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._all_handlers: list[EventHandler] = []  # Catch-all handlers
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event_type: Event type to subscribe to
            handler: Async handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe to all events.

        Args:
            handler: Async handler function
        """
        self._all_handlers.append(handler)
        logger.debug("Handler subscribed to all events")

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        handlers = self._handlers.get(event.type, []) + self._all_handlers

        if not handlers:
            logger.debug(f"No handlers for event {event.type.value}")
            return

        # Run all handlers concurrently
        tasks = []
        for handler in handlers:
            tasks.append(self._safe_call(handler, event))

        await asyncio.gather(*tasks)

    async def emit(
        self,
        event_type: EventType,
        data: dict[str, Any] | None = None,
        source: str = "nexus",
    ) -> None:
        """
        Convenience method to emit an event.

        Args:
            event_type: Type of event
            data: Event data
            source: Event source
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source,
        )
        await self.publish(event)

    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Safely call a handler, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in event handler for {event.type.value}: {e}")


# Global event bus singleton
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


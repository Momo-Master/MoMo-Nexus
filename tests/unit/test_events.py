"""
Tests for event bus.
"""

import asyncio

import pytest

from nexus.core.events import Event, EventBus, EventType


class TestEventBus:
    """Tests for EventBus."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self) -> None:
        """Test subscribing and receiving events."""
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(EventType.MESSAGE_RECEIVED, handler)

        await bus.emit(EventType.MESSAGE_RECEIVED, {"test": "data"})

        assert len(received) == 1
        assert received[0].data["test"] == "data"

    @pytest.mark.asyncio
    async def test_multiple_handlers(self) -> None:
        """Test multiple handlers for same event."""
        bus = EventBus()
        results = {"handler1": False, "handler2": False}

        async def handler1(event: Event):
            results["handler1"] = True

        async def handler2(event: Event):
            results["handler2"] = True

        bus.subscribe(EventType.DEVICE_ONLINE, handler1)
        bus.subscribe(EventType.DEVICE_ONLINE, handler2)

        await bus.emit(EventType.DEVICE_ONLINE, {"device_id": "test"})

        assert results["handler1"] is True
        assert results["handler2"] is True

    @pytest.mark.asyncio
    async def test_subscribe_all(self) -> None:
        """Test subscribing to all events."""
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event.type)

        bus.subscribe_all(handler)

        await bus.emit(EventType.MESSAGE_SENT)
        await bus.emit(EventType.DEVICE_ONLINE)
        await bus.emit(EventType.ALERT_NEW)

        assert len(received) == 3
        assert EventType.MESSAGE_SENT in received
        assert EventType.DEVICE_ONLINE in received

    @pytest.mark.asyncio
    async def test_unsubscribe(self) -> None:
        """Test unsubscribing from events."""
        bus = EventBus()
        count = {"value": 0}

        async def handler(event: Event):
            count["value"] += 1

        bus.subscribe(EventType.MESSAGE_SENT, handler)

        await bus.emit(EventType.MESSAGE_SENT)
        assert count["value"] == 1

        bus.unsubscribe(EventType.MESSAGE_SENT, handler)

        await bus.emit(EventType.MESSAGE_SENT)
        assert count["value"] == 1  # Should not increase

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self) -> None:
        """Test that error in one handler doesn't affect others."""
        bus = EventBus()
        success = {"reached": False}

        async def failing_handler(event: Event):
            raise ValueError("Test error")

        async def working_handler(event: Event):
            success["reached"] = True

        bus.subscribe(EventType.MESSAGE_SENT, failing_handler)
        bus.subscribe(EventType.MESSAGE_SENT, working_handler)

        await bus.emit(EventType.MESSAGE_SENT)

        # Working handler should still be called
        assert success["reached"] is True

    @pytest.mark.asyncio
    async def test_event_data(self) -> None:
        """Test event data is passed correctly."""
        bus = EventBus()
        received_data = {}

        async def handler(event: Event):
            received_data.update(event.data)

        bus.subscribe(EventType.DEVICE_STATUS, handler)

        await bus.emit(
            EventType.DEVICE_STATUS,
            {
                "device_id": "momo-001",
                "battery": 75,
                "status": "online",
            },
        )

        assert received_data["device_id"] == "momo-001"
        assert received_data["battery"] == 75

    @pytest.mark.asyncio
    async def test_no_handlers(self) -> None:
        """Test emitting event with no handlers."""
        bus = EventBus()

        # Should not raise
        await bus.emit(EventType.SYSTEM_ERROR, {"error": "test"})

    def test_event_creation(self) -> None:
        """Test Event model creation."""
        event = Event(
            type=EventType.ALERT_NEW,
            data={"severity": "high"},
            source="test-device",
        )

        assert event.type == EventType.ALERT_NEW
        assert event.data["severity"] == "high"
        assert event.source == "test-device"
        assert event.timestamp is not None


class TestEventType:
    """Tests for EventType enum."""

    def test_all_event_types_exist(self) -> None:
        """Verify all expected event types exist."""
        expected = [
            "MESSAGE_RECEIVED",
            "MESSAGE_SENT",
            "MESSAGE_QUEUED",
            "MESSAGE_FAILED",
            "MESSAGE_ACKED",
            "DEVICE_REGISTERED",
            "DEVICE_ONLINE",
            "DEVICE_OFFLINE",
            "DEVICE_LOST",
            "CHANNEL_UP",
            "CHANNEL_DOWN",
            "ALERT_NEW",
            "SYSTEM_STARTUP",
            "SYSTEM_SHUTDOWN",
        ]

        for event_name in expected:
            assert hasattr(EventType, event_name)


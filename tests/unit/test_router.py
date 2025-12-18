"""
Tests for message router.
"""

import asyncio

import pytest

from nexus.channels.mock import MockChannel, UnreliableChannel
from nexus.config import NexusConfig
from nexus.core.events import EventBus, EventType
from nexus.core.router import Router
from nexus.domain.enums import ChannelType, MessageType, Priority
from nexus.domain.models import Message


class TestRouter:
    """Tests for Router."""

    @pytest.fixture
    def router(self) -> Router:
        """Create router instance."""
        config = NexusConfig()
        event_bus = EventBus()
        return Router(config=config, event_bus=event_bus)

    @pytest.mark.asyncio
    async def test_register_channel(self, router: Router) -> None:
        """Test channel registration."""
        channel = MockChannel(name="test")
        router.register_channel(channel)

        assert router.get_channel(ChannelType.MOCK) is not None

    @pytest.mark.asyncio
    async def test_unregister_channel(self, router: Router) -> None:
        """Test channel unregistration."""
        channel = MockChannel(name="test")
        router.register_channel(channel)
        router.unregister_channel(ChannelType.MOCK)

        assert router.get_channel(ChannelType.MOCK) is None

    @pytest.mark.asyncio
    async def test_route_message_success(self, router: Router) -> None:
        """Test successful message routing."""
        channel = MockChannel(name="test", latency_ms=5)
        await channel.connect()
        router.register_channel(channel)

        msg = Message(
            src="nexus",
            dst="momo-001",
            type=MessageType.COMMAND,
        )

        result = await router.route(msg)

        assert result.success is True
        assert result.channel == ChannelType.MOCK
        assert len(channel.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_route_no_channels(self, router: Router) -> None:
        """Test routing with no channels available."""
        msg = Message(
            src="nexus",
            dst="momo-001",
            type=MessageType.COMMAND,
        )

        result = await router.route(msg)

        assert result.success is False
        assert result.queued is True

    @pytest.mark.asyncio
    async def test_route_channel_failure(self, router: Router) -> None:
        """Test routing when channel fails."""
        # Use channel with 100% failure rate
        channel = MockChannel(name="failing", failure_rate=1.0)
        await channel.connect()
        router.register_channel(channel)

        msg = Message(
            src="nexus",
            dst="momo-001",
            type=MessageType.COMMAND,
        )

        result = await router.route(msg)

        # Should be queued since channel failed
        assert result.success is False
        assert result.queued is True

    @pytest.mark.asyncio
    async def test_route_priority_channel_order(self, router: Router) -> None:
        """Test that priority affects channel selection."""
        channel = MockChannel(name="test")
        await channel.connect()
        router.register_channel(channel)

        # Critical message
        critical_msg = Message(
            src="nexus",
            type=MessageType.ALERT,
            pri=Priority.CRITICAL,
        )

        # Low priority message
        low_msg = Message(
            src="nexus",
            type=MessageType.DATA,
            pri=Priority.LOW,
        )

        result1 = await router.route(critical_msg)
        result2 = await router.route(low_msg)

        assert result1.success is True
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_handle_incoming_message(self, router: Router) -> None:
        """Test handling incoming message."""
        events_received = []

        async def handler(event):
            events_received.append(event)

        router._event_bus.subscribe(EventType.MESSAGE_RECEIVED, handler)

        msg = Message(
            src="momo-001",
            dst="nexus",
            type=MessageType.STATUS,
        )

        await router.handle_incoming(msg, ChannelType.MOCK)

        assert len(events_received) == 1
        assert events_received[0].data["message_id"] == msg.id

    @pytest.mark.asyncio
    async def test_handle_incoming_ack(self, router: Router) -> None:
        """Test handling ACK for pending message."""
        channel = MockChannel(name="test", echo=True)
        await channel.connect()
        router.register_channel(channel)

        msg = Message(
            src="nexus",
            dst="momo-001",
            type=MessageType.COMMAND,
            ack_required=True,
        )

        # Start routing (will wait for ACK)
        route_task = asyncio.create_task(
            router.route_with_ack(msg, timeout=1.0)
        )

        # Simulate receiving ACK
        await asyncio.sleep(0.1)
        ack = msg.create_ack(success=True)
        await router.handle_incoming(ack, ChannelType.MOCK)

        result, ack_msg = await route_task

        assert result.success is True
        assert ack_msg is not None

    @pytest.mark.asyncio
    async def test_get_stats(self, router: Router) -> None:
        """Test getting router statistics."""
        channel = MockChannel()
        await channel.connect()
        router.register_channel(channel)

        msg = Message(src="nexus", type=MessageType.PING)
        await router.route(msg)

        stats = router.get_stats()

        assert "messages_routed" in stats
        assert "queue_stats" in stats
        assert "channels" in stats

    @pytest.mark.asyncio
    async def test_start_stop(self, router: Router) -> None:
        """Test starting and stopping router."""
        await router.start()
        assert router._running is True

        await router.stop()
        assert router._running is False


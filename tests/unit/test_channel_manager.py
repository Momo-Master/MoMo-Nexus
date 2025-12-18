"""
Tests for Channel Manager.
"""

import pytest

from nexus.channels.manager import ChannelManager
from nexus.channels.mock import MockChannel
from nexus.config import NexusConfig
from nexus.core.events import EventBus, EventType
from nexus.domain.enums import ChannelType, ChannelStatus


class TestChannelManager:
    """Tests for ChannelManager."""

    @pytest.fixture
    def manager(self) -> ChannelManager:
        """Create channel manager."""
        config = NexusConfig()
        event_bus = EventBus()
        return ChannelManager(config=config, event_bus=event_bus)

    def test_register_channel(self, manager: ChannelManager) -> None:
        """Test channel registration."""
        channel = MockChannel(name="test-mock")
        manager.register_channel(channel)

        assert ChannelType.MOCK in manager.channels
        assert manager.get_channel(ChannelType.MOCK) is not None

    def test_unregister_channel(self, manager: ChannelManager) -> None:
        """Test channel unregistration."""
        channel = MockChannel()
        manager.register_channel(channel)
        manager.unregister_channel(ChannelType.MOCK)

        assert ChannelType.MOCK not in manager.channels

    @pytest.mark.asyncio
    async def test_start_stop(self, manager: ChannelManager) -> None:
        """Test manager lifecycle."""
        channel = MockChannel()
        manager.register_channel(channel)

        await manager.start()

        assert channel.is_connected
        assert manager._running

        await manager.stop()

        assert not manager._running

    @pytest.mark.asyncio
    async def test_available_channels(self, manager: ChannelManager) -> None:
        """Test getting available channels."""
        channel = MockChannel()
        manager.register_channel(channel)

        # Not connected yet
        assert len(manager.available_channels) == 0

        await manager.start()

        # Now available
        assert len(manager.available_channels) == 1

        await manager.stop()

    @pytest.mark.asyncio
    async def test_get_status(self, manager: ChannelManager) -> None:
        """Test status reporting."""
        channel = MockChannel()
        manager.register_channel(channel)

        await manager.start()

        status = manager.get_status()

        assert status["total"] == 1
        assert status["available"] == 1
        assert "mock" in status["channels"]
        assert status["channels"]["mock"]["connected"] is True

        await manager.stop()

    @pytest.mark.asyncio
    async def test_restart_channel(self, manager: ChannelManager) -> None:
        """Test channel restart."""
        channel = MockChannel()
        manager.register_channel(channel)

        await manager.start()

        success = await manager.restart_channel(ChannelType.MOCK)
        assert success is True

        await manager.stop()

    @pytest.mark.asyncio
    async def test_get_best_channel(self, manager: ChannelManager) -> None:
        """Test getting best channel."""
        fast = MockChannel(name="fast", latency_ms=10)
        slow = MockChannel(name="slow", latency_ms=100)

        manager.register_channel(fast)
        # Note: both are MOCK type, so only one will be stored
        # In real usage, different channel types would be used

        await manager.start()

        best = manager.get_best_channel()
        assert best is not None

        await manager.stop()

    @pytest.mark.asyncio
    async def test_event_emission(self, manager: ChannelManager) -> None:
        """Test events are emitted on channel state changes."""
        events = []

        async def handler(event):
            events.append(event)

        manager._event_bus.subscribe(EventType.CHANNEL_UP, handler)

        channel = MockChannel()
        manager.register_channel(channel)

        await manager.start()

        # Should have emitted CHANNEL_UP
        assert any(e.type == EventType.CHANNEL_UP for e in events)

        await manager.stop()

    def test_health_summary(self, manager: ChannelManager) -> None:
        """Test health summary."""
        channel = MockChannel()
        manager.register_channel(channel)

        # Initially empty
        summary = manager.get_health_summary()
        assert summary == {}


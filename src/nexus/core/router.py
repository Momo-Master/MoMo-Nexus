"""
Message Router - Core routing engine.

Handles intelligent message routing across multiple channels.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import TYPE_CHECKING, Any, Protocol

from nexus.config import NexusConfig, get_config
from nexus.core.events import EventBus, EventType, get_event_bus
from nexus.core.queue import MessageQueue
from nexus.domain.enums import ChannelType, Priority
from nexus.domain.models import Message, RoutingResult

if TYPE_CHECKING:
    from nexus.channels.base import BaseChannel

logger = logging.getLogger(__name__)


class RoutingError(Exception):
    """Raised when routing fails."""

    pass


class ChannelProvider(Protocol):
    """Protocol for channel provider (for dependency injection)."""

    def get_channel(self, channel_type: ChannelType) -> BaseChannel | None:
        """Get channel by type."""
        ...

    def get_available_channels(self) -> list[BaseChannel]:
        """Get all available channels."""
        ...


class Router:
    """
    Message Router - Intelligent multi-channel routing.

    Features:
    - Priority-based channel selection
    - Automatic failover
    - Store-and-forward
    - ACK handling
    - Retry with backoff
    """

    def __init__(
        self,
        config: NexusConfig | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._config = config or get_config()
        self._event_bus = event_bus or get_event_bus()
        self._channels: dict[ChannelType, BaseChannel] = {}
        self._queue = MessageQueue(
            max_size=self._config.routing.queue_max_size,
            max_retries=self._config.routing.max_retries,
            backoff_base=self._config.routing.retry_backoff_base,
            backoff_max=self._config.routing.retry_backoff_max,
        )
        self._pending_acks: dict[str, asyncio.Future[Message]] = {}
        self._running = False
        self._worker_task: asyncio.Task | None = None

        # Statistics
        self._stats = {
            "messages_routed": 0,
            "messages_queued": 0,
            "routing_failures": 0,
            "acks_received": 0,
            "acks_timeout": 0,
        }

    def register_channel(self, channel: BaseChannel) -> None:
        """
        Register a channel for routing.

        Args:
            channel: Channel instance to register
        """
        self._channels[channel.channel_type] = channel
        logger.info(f"Registered channel: {channel.channel_type.value}")

    def unregister_channel(self, channel_type: ChannelType) -> None:
        """Unregister a channel."""
        self._channels.pop(channel_type, None)
        logger.info(f"Unregistered channel: {channel_type.value}")

    def get_channel(self, channel_type: ChannelType) -> BaseChannel | None:
        """Get channel by type."""
        return self._channels.get(channel_type)

    def get_available_channels(self) -> list[BaseChannel]:
        """Get all available (up/degraded) channels."""
        return [ch for ch in self._channels.values() if ch.is_available()]

    async def route(self, message: Message) -> RoutingResult:
        """
        Route a message to appropriate channel(s).

        Args:
            message: Message to route

        Returns:
            RoutingResult with success/failure info
        """
        start_time = time.time()
        channels_tried: list[ChannelType] = []

        # Get channel order based on priority
        channel_order = self._get_channel_order(message.pri)

        for channel_type in channel_order:
            channel = self._channels.get(channel_type)
            if not channel or not channel.is_available():
                continue

            channels_tried.append(channel_type)

            try:
                success = await channel.send(message)
                if success:
                    duration_ms = (time.time() - start_time) * 1000
                    self._stats["messages_routed"] += 1

                    # Emit event
                    await self._event_bus.emit(
                        EventType.MESSAGE_SENT,
                        {
                            "message_id": message.id,
                            "channel": channel_type.value,
                            "destination": message.dst,
                        },
                    )

                    logger.debug(
                        f"Message {message.id} sent via {channel_type.value} "
                        f"in {duration_ms:.1f}ms"
                    )

                    return RoutingResult(
                        message_id=message.id,
                        success=True,
                        channel=channel_type,
                        channels_tried=channels_tried,
                        duration_ms=duration_ms,
                    )

            except Exception as e:
                logger.warning(f"Channel {channel_type.value} failed: {e}")
                continue

        # All channels failed - queue message
        queued = await self._queue.enqueue(message)
        duration_ms = (time.time() - start_time) * 1000

        if queued:
            self._stats["messages_queued"] += 1
            await self._event_bus.emit(
                EventType.MESSAGE_QUEUED,
                {"message_id": message.id, "reason": "all_channels_failed"},
            )
            logger.info(f"Message {message.id} queued (all channels unavailable)")
        else:
            self._stats["routing_failures"] += 1
            await self._event_bus.emit(
                EventType.MESSAGE_FAILED,
                {"message_id": message.id, "reason": "queue_full"},
            )
            logger.error(f"Message {message.id} dropped (queue full)")

        return RoutingResult(
            message_id=message.id,
            success=False,
            channels_tried=channels_tried,
            queued=queued,
            error="All channels unavailable" if not queued else None,
            duration_ms=duration_ms,
        )

    async def route_with_ack(
        self,
        message: Message,
        timeout: float | None = None,
    ) -> tuple[RoutingResult, Message | None]:
        """
        Route message and wait for ACK.

        Args:
            message: Message to send
            timeout: ACK timeout (uses config default if None)

        Returns:
            Tuple of (RoutingResult, ACK message or None)
        """
        message.ack_required = True
        timeout = timeout or self._config.routing.ack_timeout

        # Create future for ACK
        ack_future: asyncio.Future[Message] = asyncio.Future()
        self._pending_acks[message.id] = ack_future

        try:
            # Route the message
            result = await self.route(message)

            if not result.success:
                return result, None

            # Wait for ACK
            try:
                ack_message = await asyncio.wait_for(ack_future, timeout)
                self._stats["acks_received"] += 1
                return result, ack_message
            except TimeoutError:
                self._stats["acks_timeout"] += 1
                logger.warning(f"ACK timeout for message {message.id}")
                result.error = "ACK timeout"
                return result, None

        finally:
            self._pending_acks.pop(message.id, None)

    async def handle_incoming(self, message: Message, channel: ChannelType) -> None:
        """
        Handle incoming message from a channel.

        Args:
            message: Received message
            channel: Channel it was received on
        """
        message.ch = channel

        # Emit receive event
        await self._event_bus.emit(
            EventType.MESSAGE_RECEIVED,
            {
                "message_id": message.id,
                "type": message.type,
                "source": message.src,
                "channel": channel.value,
            },
        )

        # Check if this is an ACK for a pending message
        if message.ack_id and message.ack_id in self._pending_acks:
            future = self._pending_acks[message.ack_id]
            if not future.done():
                future.set_result(message)
                await self._event_bus.emit(
                    EventType.MESSAGE_ACKED,
                    {"message_id": message.ack_id, "ack_id": message.id},
                )
            return

        # If message requires ACK, send it
        if message.needs_ack():
            ack = message.create_ack(success=True)
            await self.route(ack)

    def _get_channel_order(self, priority: Priority) -> list[ChannelType]:
        """
        Get ordered list of channels for priority.

        Args:
            priority: Message priority

        Returns:
            Ordered list of channel types to try
        """
        # Get from config
        channel_names = self._config.routing.priority_channels.get(
            priority.value if isinstance(priority, Priority) else priority,
            ["lora", "wifi", "cellular"],
        )

        result = []
        for name in channel_names:
            try:
                channel_type = ChannelType(name)
                if channel_type in self._channels:
                    result.append(channel_type)
            except ValueError:
                continue

        # Add any registered channels not in the list
        for channel_type in self._channels:
            if channel_type not in result:
                result.append(channel_type)

        return result

    async def start(self) -> None:
        """Start the router and queue worker."""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._queue_worker())
        logger.info("Router started")

    async def stop(self) -> None:
        """Stop the router."""
        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

        logger.info("Router stopped")

    async def _queue_worker(self) -> None:
        """Background worker to process queued messages."""
        logger.info("Queue worker started")

        while self._running:
            try:
                message = await self._queue.dequeue(timeout=1.0)
                if message is None:
                    continue

                result = await self.route(message)

                if not result.success and not result.queued:
                    # Re-queue with retry tracking
                    await self._queue.mark_failed(message)
                else:
                    await self._queue.mark_success(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue worker error: {e}")
                await asyncio.sleep(1)

        logger.info("Queue worker stopped")

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        stats = dict(self._stats)
        stats["queue_stats"] = self._queue.get_stats()
        stats["channels"] = {
            ct.value: {
                "available": ch.is_available(),
                "status": ch.status.value,
            }
            for ct, ch in self._channels.items()
        }
        return stats

    async def get_queue_size(self) -> int:
        """Get current queue size."""
        return await self._queue.size()


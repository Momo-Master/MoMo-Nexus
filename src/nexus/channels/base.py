"""
Abstract base class for communication channels.

All channel drivers (LoRa, Cellular, WiFi, etc.) inherit from this.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Coroutine

from nexus.domain.enums import ChannelStatus, ChannelType
from nexus.domain.models import Channel, ChannelMetrics, Message

logger = logging.getLogger(__name__)


class ChannelError(Exception):
    """Base exception for channel errors."""

    pass


class ConnectionError(ChannelError):
    """Channel connection failed."""

    pass


class SendError(ChannelError):
    """Message send failed."""

    pass


class TimeoutError(ChannelError):
    """Operation timed out."""

    pass


# Type alias for message handlers
MessageHandler = Callable[[Message], Coroutine[Any, Any, None]]


class BaseChannel(ABC):
    """
    Abstract base class for all communication channels.

    Subclasses must implement:
    - _connect()
    - _disconnect()
    - _send()
    - _health_check()

    Optional overrides:
    - _on_message() for receiving
    """

    def __init__(
        self,
        channel_type: ChannelType,
        name: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._type = channel_type
        self._name = name or channel_type.value
        self._config = config or {}
        self._status = ChannelStatus.UNKNOWN
        self._enabled = True
        self._metrics = ChannelMetrics()
        self._message_handlers: list[MessageHandler] = []
        self._connected = False
        self._lock = asyncio.Lock()

        # Health check
        self._health_check_task: asyncio.Task | None = None
        self._health_check_interval = 30  # seconds
        self._consecutive_failures = 0
        self._failure_threshold_degraded = 3
        self._failure_threshold_down = 10

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def channel_type(self) -> ChannelType:
        """Get channel type."""
        return self._type

    @property
    def name(self) -> str:
        """Get channel name."""
        return self._name

    @property
    def status(self) -> ChannelStatus:
        """Get current channel status."""
        return self._status

    @property
    def enabled(self) -> bool:
        """Check if channel is enabled."""
        return self._enabled

    @property
    def is_connected(self) -> bool:
        """Check if channel is connected."""
        return self._connected

    @property
    def metrics(self) -> ChannelMetrics:
        """Get channel metrics."""
        return self._metrics

    # =========================================================================
    # Public Methods
    # =========================================================================

    def is_available(self) -> bool:
        """Check if channel is available for sending."""
        return (
            self._enabled
            and self._connected
            and self._status in (ChannelStatus.UP, ChannelStatus.DEGRADED)
        )

    async def connect(self) -> bool:
        """
        Connect the channel.

        Returns:
            True if connected successfully
        """
        async with self._lock:
            if self._connected:
                return True

            try:
                logger.info(f"Connecting channel: {self._name}")
                await self._connect()
                self._connected = True
                self._status = ChannelStatus.UP
                self._consecutive_failures = 0
                logger.info(f"Channel connected: {self._name}")
                return True

            except Exception as e:
                logger.error(f"Channel connection failed: {self._name}: {e}")
                self._status = ChannelStatus.DOWN
                return False

    async def disconnect(self) -> None:
        """Disconnect the channel."""
        async with self._lock:
            if not self._connected:
                return

            try:
                logger.info(f"Disconnecting channel: {self._name}")
                await self._disconnect()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connected = False
                self._status = ChannelStatus.DOWN
                logger.info(f"Channel disconnected: {self._name}")

    async def send(self, message: Message, timeout: float = 10.0) -> bool:
        """
        Send a message through this channel.

        Args:
            message: Message to send
            timeout: Send timeout in seconds

        Returns:
            True if sent successfully

        Raises:
            ChannelError: If send fails
        """
        if not self.is_available():
            raise ChannelError(f"Channel {self._name} not available")

        start_time = asyncio.get_event_loop().time()

        try:
            async with asyncio.timeout(timeout):
                success = await self._send(message)

            # Update metrics
            elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._update_metrics(success, elapsed_ms, len(str(message.data)))

            if success:
                self._consecutive_failures = 0
                if self._status == ChannelStatus.DEGRADED:
                    self._status = ChannelStatus.UP
            else:
                self._handle_failure()

            return success

        except asyncio.TimeoutError:
            self._handle_failure()
            raise TimeoutError(f"Send timeout on channel {self._name}")

        except Exception as e:
            self._handle_failure()
            raise SendError(f"Send failed on channel {self._name}: {e}")

    def add_message_handler(self, handler: MessageHandler) -> None:
        """Add handler for incoming messages."""
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: MessageHandler) -> None:
        """Remove a message handler."""
        try:
            self._message_handlers.remove(handler)
        except ValueError:
            pass

    async def start_health_check(self) -> None:
        """Start periodic health checks."""
        if self._health_check_task is not None:
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.debug(f"Health check started for {self._name}")

    async def stop_health_check(self) -> None:
        """Stop health checks."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    def to_model(self) -> Channel:
        """Convert to Channel domain model."""
        return Channel(
            name=self._name,
            type=self._type,
            status=self._status,
            enabled=self._enabled,
            metrics=self._metrics,
        )

    # =========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    async def _connect(self) -> None:
        """
        Perform actual connection.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """Perform actual disconnection."""
        pass

    @abstractmethod
    async def _send(self, message: Message) -> bool:
        """
        Perform actual send.

        Args:
            message: Message to send

        Returns:
            True if sent successfully
        """
        pass

    @abstractmethod
    async def _health_check(self) -> bool:
        """
        Perform health check.

        Returns:
            True if healthy
        """
        pass

    # =========================================================================
    # Protected Methods
    # =========================================================================

    async def _on_message(self, message: Message) -> None:
        """
        Handle incoming message.

        Override in subclasses for custom handling.
        """
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")

    def _update_metrics(
        self,
        success: bool,
        latency_ms: float,
        bytes_sent: int,
    ) -> None:
        """Update channel metrics after send."""
        if success:
            self._metrics.messages_sent += 1
            self._metrics.bytes_sent += bytes_sent
            self._metrics.last_success = datetime.now()

            # Exponential moving average for latency
            alpha = 0.3
            self._metrics.latency_ms = (
                alpha * latency_ms + (1 - alpha) * self._metrics.latency_ms
            )
        else:
            self._metrics.last_failure = datetime.now()

    def _handle_failure(self) -> None:
        """Handle a failure, update status if needed."""
        self._consecutive_failures += 1
        self._metrics.consecutive_failures = self._consecutive_failures

        if self._consecutive_failures >= self._failure_threshold_down:
            if self._status != ChannelStatus.DOWN:
                logger.warning(f"Channel {self._name} marked DOWN")
                self._status = ChannelStatus.DOWN
        elif self._consecutive_failures >= self._failure_threshold_degraded:
            if self._status == ChannelStatus.UP:
                logger.warning(f"Channel {self._name} marked DEGRADED")
                self._status = ChannelStatus.DEGRADED

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)

                if not self._enabled:
                    continue

                try:
                    healthy = await self._health_check()

                    if healthy:
                        self._consecutive_failures = 0
                        if self._status != ChannelStatus.UP:
                            logger.info(f"Channel {self._name} is UP")
                            self._status = ChannelStatus.UP
                    else:
                        self._handle_failure()

                except Exception as e:
                    logger.warning(f"Health check failed for {self._name}: {e}")
                    self._handle_failure()

            except asyncio.CancelledError:
                break

    # =========================================================================
    # Dunder Methods
    # =========================================================================

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name}, status={self._status.value})"


"""
Mock channel for testing.

Simulates a communication channel with configurable behavior.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from nexus.channels.base import BaseChannel
from nexus.domain.enums import ChannelType
from nexus.domain.models import Message

logger = logging.getLogger(__name__)


class MockChannel(BaseChannel):
    """
    Mock channel for testing.

    Configurable:
    - Latency simulation
    - Failure rate
    - Message echo (loopback)
    """

    def __init__(
        self,
        name: str = "mock",
        latency_ms: float = 100.0,
        failure_rate: float = 0.0,
        echo: bool = False,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            channel_type=ChannelType.MOCK,
            name=name,
            config=config,
        )
        self._latency_ms = latency_ms
        self._failure_rate = failure_rate
        self._echo = echo
        self._sent_messages: list[Message] = []
        self._received_messages: list[Message] = []

    # =========================================================================
    # Test Helpers
    # =========================================================================

    @property
    def sent_messages(self) -> list[Message]:
        """Get list of sent messages (for testing)."""
        return self._sent_messages.copy()

    @property
    def received_messages(self) -> list[Message]:
        """Get list of received messages (for testing)."""
        return self._received_messages.copy()

    def clear_messages(self) -> None:
        """Clear message history."""
        self._sent_messages.clear()
        self._received_messages.clear()

    def set_latency(self, latency_ms: float) -> None:
        """Set simulated latency."""
        self._latency_ms = latency_ms

    def set_failure_rate(self, rate: float) -> None:
        """Set failure rate (0.0 - 1.0)."""
        self._failure_rate = max(0.0, min(1.0, rate))

    async def inject_message(self, message: Message) -> None:
        """
        Inject a message as if received from external source.

        Useful for testing receive handlers.
        """
        self._received_messages.append(message)
        await self._on_message(message)

    # =========================================================================
    # BaseChannel Implementation
    # =========================================================================

    async def _connect(self) -> None:
        """Simulate connection."""
        await asyncio.sleep(0.1)  # Simulate connection time
        logger.debug(f"Mock channel {self._name} connected")

    async def _disconnect(self) -> None:
        """Simulate disconnection."""
        await asyncio.sleep(0.05)
        logger.debug(f"Mock channel {self._name} disconnected")

    async def _send(self, message: Message) -> bool:
        """
        Simulate sending a message.

        Args:
            message: Message to send

        Returns:
            True if "sent" successfully
        """
        # Simulate latency
        latency = self._latency_ms / 1000.0
        if latency > 0:
            # Add some jitter
            jitter = latency * 0.1 * random.random()
            await asyncio.sleep(latency + jitter)

        # Simulate failures
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            logger.debug(f"Mock channel {self._name}: simulated failure")
            return False

        # Store for inspection
        self._sent_messages.append(message)
        logger.debug(f"Mock channel {self._name}: sent message {message.id}")

        # Echo back if enabled
        if self._echo and message.dst:
            echo_msg = Message(
                src=message.dst,
                dst=message.src,
                type=message.type,
                data=message.data,
            )
            asyncio.create_task(self._delayed_echo(echo_msg))

        return True

    async def _health_check(self) -> bool:
        """Simulate health check."""
        await asyncio.sleep(0.01)
        # Fail health check based on failure rate
        return random.random() >= self._failure_rate

    async def _delayed_echo(self, message: Message, delay: float = 0.1) -> None:
        """Echo message after delay."""
        await asyncio.sleep(delay)
        await self._on_message(message)


class LoopbackChannel(MockChannel):
    """
    Loopback channel that echoes all messages.

    Useful for testing routing logic.
    """

    def __init__(self, name: str = "loopback") -> None:
        super().__init__(
            name=name,
            latency_ms=10.0,
            failure_rate=0.0,
            echo=True,
        )


class UnreliableChannel(MockChannel):
    """
    Unreliable channel with high failure rate.

    Useful for testing failover and retry logic.
    """

    def __init__(
        self,
        name: str = "unreliable",
        failure_rate: float = 0.5,
    ) -> None:
        super().__init__(
            name=name,
            latency_ms=500.0,
            failure_rate=failure_rate,
            echo=False,
        )


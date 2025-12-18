"""
Priority message queue with persistence.

Supports priority-based ordering and SQLite persistence.
"""

from __future__ import annotations

import asyncio
import heapq
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nexus.domain.enums import Priority
from nexus.domain.models import Message

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueueItem:
    """
    Priority queue item wrapper.

    Uses negative priority value for max-heap behavior (critical first).
    """

    priority_value: int
    timestamp: float
    message: Message = field(compare=False)
    retry_count: int = field(default=0, compare=False)
    next_retry_at: datetime | None = field(default=None, compare=False)

    @classmethod
    def from_message(cls, message: Message) -> "QueueItem":
        """Create queue item from message."""
        # Priority ordering: CRITICAL=0, HIGH=1, NORMAL=2, LOW=3, BULK=4
        priority_map = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.NORMAL: 2,
            Priority.LOW: 3,
            Priority.BULK: 4,
        }
        priority_value = priority_map.get(Priority(message.pri), 2)

        return cls(
            priority_value=priority_value,
            timestamp=message.created_at.timestamp(),
            message=message,
        )


class PriorityQueue:
    """
    In-memory priority queue.

    Uses heapq for efficient priority ordering.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._heap: list[QueueItem] = []
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()

    async def put(self, message: Message) -> bool:
        """
        Add message to queue.

        Args:
            message: Message to queue

        Returns:
            True if added, False if queue full
        """
        async with self._lock:
            if len(self._heap) >= self._max_size:
                logger.warning(f"Queue full ({self._max_size}), dropping message {message.id}")
                return False

            item = QueueItem.from_message(message)
            heapq.heappush(self._heap, item)
            self._not_empty.set()
            logger.debug(f"Queued message {message.id} with priority {message.pri}")
            return True

    async def get(self, timeout: float | None = None) -> Message | None:
        """
        Get highest priority message.

        Args:
            timeout: Max time to wait (None = wait forever)

        Returns:
            Message or None if timeout
        """
        try:
            if timeout is not None:
                await asyncio.wait_for(self._not_empty.wait(), timeout)
            else:
                await self._not_empty.wait()
        except asyncio.TimeoutError:
            return None

        async with self._lock:
            if not self._heap:
                self._not_empty.clear()
                return None

            item = heapq.heappop(self._heap)

            if not self._heap:
                self._not_empty.clear()

            return item.message

    async def peek(self) -> Message | None:
        """Look at highest priority message without removing."""
        async with self._lock:
            if self._heap:
                return self._heap[0].message
            return None

    async def size(self) -> int:
        """Get queue size."""
        async with self._lock:
            return len(self._heap)

    async def is_empty(self) -> bool:
        """Check if queue is empty."""
        async with self._lock:
            return len(self._heap) == 0

    async def clear(self) -> int:
        """Clear all messages, return count cleared."""
        async with self._lock:
            count = len(self._heap)
            self._heap.clear()
            self._not_empty.clear()
            return count


class MessageQueue:
    """
    High-level message queue with retry support.

    Wraps PriorityQueue with retry logic and statistics.
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        backoff_max: float = 60.0,
    ) -> None:
        self._queue = PriorityQueue(max_size)
        self._retry_queue: dict[str, QueueItem] = {}  # message_id -> item
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "enqueued": 0,
            "dequeued": 0,
            "retried": 0,
            "dropped": 0,
            "max_size_reached": 0,
        }

    async def enqueue(self, message: Message) -> bool:
        """
        Add message to queue.

        Args:
            message: Message to queue

        Returns:
            True if added successfully
        """
        success = await self._queue.put(message)
        if success:
            self._stats["enqueued"] += 1
        else:
            self._stats["max_size_reached"] += 1
        return success

    async def dequeue(self, timeout: float | None = None) -> Message | None:
        """
        Get next message to process.

        Args:
            timeout: Max wait time

        Returns:
            Message or None
        """
        # First check retry queue for messages ready to retry
        async with self._lock:
            now = datetime.now()
            ready_retries = [
                (msg_id, item)
                for msg_id, item in self._retry_queue.items()
                if item.next_retry_at and item.next_retry_at <= now
            ]

            if ready_retries:
                msg_id, item = ready_retries[0]
                del self._retry_queue[msg_id]
                self._stats["retried"] += 1
                return item.message

        # Otherwise get from main queue
        message = await self._queue.get(timeout)
        if message:
            self._stats["dequeued"] += 1
        return message

    async def mark_failed(self, message: Message) -> bool:
        """
        Mark message as failed, schedule retry.

        Args:
            message: Failed message

        Returns:
            True if will retry, False if max retries reached
        """
        message.retries += 1

        if message.retries >= self._max_retries:
            logger.warning(
                f"Message {message.id} exceeded max retries ({self._max_retries}), dropping"
            )
            self._stats["dropped"] += 1
            return False

        # Calculate backoff delay
        delay = min(
            self._backoff_base * (2 ** (message.retries - 1)),
            self._backoff_max,
        )

        from datetime import timedelta

        item = QueueItem.from_message(message)
        item.retry_count = message.retries
        item.next_retry_at = datetime.now() + timedelta(seconds=delay)

        async with self._lock:
            self._retry_queue[message.id] = item

        logger.info(
            f"Message {message.id} scheduled for retry #{message.retries} in {delay:.1f}s"
        )
        return True

    async def mark_success(self, message: Message) -> None:
        """Mark message as successfully sent."""
        async with self._lock:
            self._retry_queue.pop(message.id, None)

    async def size(self) -> int:
        """Get total queue size (main + retry)."""
        main_size = await self._queue.size()
        async with self._lock:
            return main_size + len(self._retry_queue)

    async def pending_retries(self) -> int:
        """Get number of messages pending retry."""
        async with self._lock:
            return len(self._retry_queue)

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return dict(self._stats)


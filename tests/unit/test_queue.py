"""
Tests for message queue.
"""

import asyncio

import pytest

from nexus.core.queue import MessageQueue, PriorityQueue
from nexus.domain.enums import MessageType, Priority
from nexus.domain.models import Message


class TestPriorityQueue:
    """Tests for PriorityQueue."""

    @pytest.mark.asyncio
    async def test_put_and_get(self) -> None:
        """Test basic put and get."""
        queue = PriorityQueue()

        msg = Message(src="test", type=MessageType.PING)
        await queue.put(msg)

        result = await queue.get()

        assert result is not None
        assert result.id == msg.id

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        """Test that higher priority messages come first."""
        queue = PriorityQueue()

        low = Message(src="test", type=MessageType.DATA, pri=Priority.LOW)
        normal = Message(src="test", type=MessageType.DATA, pri=Priority.NORMAL)
        critical = Message(src="test", type=MessageType.ALERT, pri=Priority.CRITICAL)

        # Add in wrong order
        await queue.put(low)
        await queue.put(normal)
        await queue.put(critical)

        # Should come out in priority order
        first = await queue.get()
        assert first.pri == Priority.CRITICAL

        second = await queue.get()
        assert second.pri == Priority.NORMAL

        third = await queue.get()
        assert third.pri == Priority.LOW

    @pytest.mark.asyncio
    async def test_max_size(self) -> None:
        """Test queue max size enforcement."""
        queue = PriorityQueue(max_size=2)

        msg1 = Message(src="test", type=MessageType.PING)
        msg2 = Message(src="test", type=MessageType.PING)
        msg3 = Message(src="test", type=MessageType.PING)

        assert await queue.put(msg1) is True
        assert await queue.put(msg2) is True
        assert await queue.put(msg3) is False  # Should be rejected

        assert await queue.size() == 2

    @pytest.mark.asyncio
    async def test_get_with_timeout(self) -> None:
        """Test get with timeout on empty queue."""
        queue = PriorityQueue()

        result = await queue.get(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_peek(self) -> None:
        """Test peeking at queue."""
        queue = PriorityQueue()

        msg = Message(src="test", type=MessageType.PING)
        await queue.put(msg)

        # Peek should not remove
        peeked = await queue.peek()
        assert peeked is not None
        assert await queue.size() == 1

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """Test clearing queue."""
        queue = PriorityQueue()

        await queue.put(Message(src="test", type=MessageType.PING))
        await queue.put(Message(src="test", type=MessageType.PING))

        count = await queue.clear()
        assert count == 2
        assert await queue.is_empty() is True


class TestMessageQueue:
    """Tests for MessageQueue with retry support."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self) -> None:
        """Test basic enqueue and dequeue."""
        queue = MessageQueue()

        msg = Message(src="test", type=MessageType.PING)
        await queue.enqueue(msg)

        result = await queue.dequeue(timeout=1.0)

        assert result is not None
        assert result.id == msg.id

    @pytest.mark.asyncio
    async def test_mark_failed_retries(self) -> None:
        """Test marking message as failed schedules retry."""
        queue = MessageQueue(max_retries=3)

        msg = Message(src="test", type=MessageType.COMMAND)
        await queue.enqueue(msg)

        # Dequeue and fail
        dequeued = await queue.dequeue(timeout=0.1)
        assert dequeued is not None

        will_retry = await queue.mark_failed(dequeued)
        assert will_retry is True
        assert dequeued.retries == 1

        # Should be in retry queue
        pending = await queue.pending_retries()
        assert pending == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        """Test message dropped after max retries."""
        queue = MessageQueue(max_retries=2)

        msg = Message(src="test", type=MessageType.COMMAND)
        msg.retries = 2  # Already at max

        will_retry = await queue.mark_failed(msg)
        assert will_retry is False

    @pytest.mark.asyncio
    async def test_mark_success(self) -> None:
        """Test marking message as successful."""
        queue = MessageQueue()

        msg = Message(src="test", type=MessageType.COMMAND)

        # Simulate retry pending
        await queue.mark_failed(msg)
        await queue.mark_success(msg)

        pending = await queue.pending_retries()
        assert pending == 0

    @pytest.mark.asyncio
    async def test_get_stats(self) -> None:
        """Test queue statistics."""
        queue = MessageQueue()

        msg = Message(src="test", type=MessageType.PING)
        await queue.enqueue(msg)
        await queue.dequeue(timeout=0.1)

        stats = queue.get_stats()

        assert stats["enqueued"] == 1
        assert stats["dequeued"] == 1


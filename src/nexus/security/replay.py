"""
Replay protection.

Prevents message replay attacks using nonce tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NonceEntry:
    """Tracked nonce entry."""

    nonce: str
    timestamp: int
    device_id: str | None = None
    message_id: str | None = None


class ReplayGuard:
    """
    Replay attack protection.

    Features:
    - Nonce tracking with expiration
    - Sliding window for timestamp validation
    - Per-device nonce isolation
    - Memory-efficient LRU cleanup
    """

    def __init__(
        self,
        window_seconds: int = 300,  # 5 minutes
        max_nonces: int = 100000,
        cleanup_interval: int = 60,
    ) -> None:
        """
        Initialize replay guard.

        Args:
            window_seconds: Time window for valid messages
            max_nonces: Maximum nonces to track
            cleanup_interval: Cleanup interval in seconds
        """
        self._window = window_seconds
        self._max_nonces = max_nonces
        self._cleanup_interval = cleanup_interval

        # Global nonce tracking (LRU)
        self._nonces: OrderedDict[str, NonceEntry] = OrderedDict()

        # Per-device nonce tracking
        self._device_nonces: dict[str, set[str]] = {}

        # Sequence tracking per device
        self._sequences: dict[str, int] = {}

        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.debug("Replay guard started")

    async def stop(self) -> None:
        """Stop background cleanup task."""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        logger.debug("Replay guard stopped")

    # =========================================================================
    # Nonce Validation
    # =========================================================================

    async def check_nonce(
        self,
        nonce: str,
        timestamp: int,
        device_id: str | None = None,
        message_id: str | None = None,
    ) -> bool:
        """
        Check if nonce is valid (not replayed).

        Args:
            nonce: Message nonce
            timestamp: Message timestamp
            device_id: Optional device ID for isolation
            message_id: Optional message ID for tracking

        Returns:
            True if nonce is valid (first time seen)
        """
        now = int(time.time())

        # Check timestamp freshness
        age = abs(now - timestamp)
        if age > self._window:
            logger.warning(f"Nonce rejected: timestamp too old ({age}s)")
            return False

        # Check for future timestamps (clock skew tolerance: 30s)
        if timestamp > now + 30:
            logger.warning(f"Nonce rejected: timestamp in future")
            return False

        async with self._lock:
            # Build composite key for device isolation
            if device_id:
                key = f"{device_id}:{nonce}"
            else:
                key = nonce

            # Check if nonce was seen
            if key in self._nonces:
                logger.warning(f"Nonce rejected: replay detected ({nonce[:16]}...)")
                return False

            # Record nonce
            entry = NonceEntry(
                nonce=nonce,
                timestamp=timestamp,
                device_id=device_id,
                message_id=message_id,
            )
            self._nonces[key] = entry
            self._nonces.move_to_end(key)

            # Track per-device
            if device_id:
                if device_id not in self._device_nonces:
                    self._device_nonces[device_id] = set()
                self._device_nonces[device_id].add(nonce)

            # LRU eviction if over limit
            while len(self._nonces) > self._max_nonces:
                oldest_key, _ = self._nonces.popitem(last=False)
                # Also remove from device tracking
                if ":" in oldest_key:
                    dev_id, old_nonce = oldest_key.split(":", 1)
                    if dev_id in self._device_nonces:
                        self._device_nonces[dev_id].discard(old_nonce)

        return True

    async def record_nonce(
        self,
        nonce: str,
        timestamp: int,
        device_id: str | None = None,
    ) -> None:
        """
        Record a nonce without validation.

        Use when you've already validated and want to track.
        """
        async with self._lock:
            key = f"{device_id}:{nonce}" if device_id else nonce
            self._nonces[key] = NonceEntry(
                nonce=nonce,
                timestamp=timestamp,
                device_id=device_id,
            )

    # =========================================================================
    # Sequence Validation
    # =========================================================================

    async def check_sequence(
        self,
        device_id: str,
        sequence: int,
        allow_gap: int = 100,
    ) -> bool:
        """
        Check if sequence number is valid.

        Args:
            device_id: Device ID
            sequence: Sequence number
            allow_gap: Maximum allowed gap

        Returns:
            True if sequence is valid
        """
        async with self._lock:
            last_seq = self._sequences.get(device_id, -1)

            # First message or valid increment
            if sequence > last_seq:
                # Check for suspicious gaps
                if last_seq >= 0 and sequence - last_seq > allow_gap:
                    logger.warning(
                        f"Large sequence gap for {device_id}: "
                        f"{last_seq} -> {sequence}"
                    )

                self._sequences[device_id] = sequence
                return True

            # Replay or out-of-order
            logger.warning(
                f"Sequence rejected for {device_id}: "
                f"got {sequence}, expected > {last_seq}"
            )
            return False

    async def get_next_sequence(self, device_id: str) -> int:
        """Get next sequence number for device."""
        async with self._lock:
            current = self._sequences.get(device_id, 0)
            next_seq = current + 1
            self._sequences[device_id] = next_seq
            return next_seq

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def _cleanup_loop(self) -> None:
        """Background cleanup of expired nonces."""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Replay guard cleanup error: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired nonces."""
        now = int(time.time())
        cutoff = now - self._window
        removed = 0

        async with self._lock:
            # Find expired entries
            expired = []
            for key, entry in self._nonces.items():
                if entry.timestamp < cutoff:
                    expired.append(key)

            # Remove expired
            for key in expired:
                entry = self._nonces.pop(key)
                removed += 1

                # Also remove from device tracking
                if entry.device_id and entry.device_id in self._device_nonces:
                    self._device_nonces[entry.device_id].discard(entry.nonce)

        if removed > 0:
            logger.debug(f"Cleaned up {removed} expired nonces")

    async def clear(self) -> None:
        """Clear all tracked nonces."""
        async with self._lock:
            self._nonces.clear()
            self._device_nonces.clear()
            self._sequences.clear()

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get replay guard statistics."""
        async with self._lock:
            return {
                "total_nonces": len(self._nonces),
                "devices_tracked": len(self._device_nonces),
                "sequences_tracked": len(self._sequences),
                "max_nonces": self._max_nonces,
                "window_seconds": self._window,
            }


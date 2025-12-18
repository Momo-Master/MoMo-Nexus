"""
SQLite database layer for MoMo-Nexus.

Uses aiosqlite for async operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from nexus.domain.enums import DeviceStatus, DeviceType, MessageType, Priority
from nexus.domain.models import Device, GPSLocation, Message

logger = logging.getLogger(__name__)


# =============================================================================
# Database Schema
# =============================================================================

SCHEMA_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    dst TEXT,
    type TEXT NOT NULL,
    priority TEXT DEFAULT 'normal',
    channel TEXT,
    timestamp INTEGER NOT NULL,
    ack_required INTEGER DEFAULT 0,
    ack_id TEXT,
    data TEXT,
    retries INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_src ON messages(src);
CREATE INDEX IF NOT EXISTS idx_messages_dst ON messages(dst);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
"""

SCHEMA_DEVICES = """
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT,
    status TEXT DEFAULT 'unregistered',
    channels TEXT,
    preferred_channel TEXT,
    last_channel TEXT,
    last_seen TEXT,
    last_message_id TEXT,
    version TEXT,
    latitude REAL,
    longitude REAL,
    altitude REAL,
    battery INTEGER,
    uptime INTEGER,
    capabilities TEXT,
    metadata TEXT,
    registered_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(type);
"""

SCHEMA_QUEUE = """
CREATE TABLE IF NOT EXISTS message_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    message_data TEXT NOT NULL,
    priority INTEGER NOT NULL,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_queue_priority ON message_queue(priority);
CREATE INDEX IF NOT EXISTS idx_queue_next_retry ON message_queue(next_retry_at);
"""


# =============================================================================
# Base Store
# =============================================================================


class BaseStore:
    """Base class for database stores."""

    def __init__(self, db_path: str = "data/nexus.db") -> None:
        self._db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to database and initialize schema."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        self._db.row_factory = aiosqlite.Row
        await self._init_schema()
        logger.info(f"Database connected: {self._db_path}")

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("Database disconnected")

    async def _init_schema(self) -> None:
        """Initialize database schema. Override in subclasses."""
        pass

    async def _execute(self, query: str, params: tuple = ()) -> None:
        """Execute a query."""
        if not self._db:
            raise RuntimeError("Database not connected")
        async with self._lock:
            await self._db.execute(query, params)
            await self._db.commit()

    async def _fetchone(self, query: str, params: tuple = ()) -> dict | None:
        """Fetch one row."""
        if not self._db:
            raise RuntimeError("Database not connected")
        async with self._lock:
            cursor = await self._db.execute(query, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        """Fetch all rows."""
        if not self._db:
            raise RuntimeError("Database not connected")
        async with self._lock:
            cursor = await self._db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# =============================================================================
# Message Store
# =============================================================================


class MessageStore(BaseStore):
    """Store for messages."""

    async def _init_schema(self) -> None:
        if self._db:
            await self._db.executescript(SCHEMA_MESSAGES)
            await self._db.commit()

    async def save(self, message: Message) -> None:
        """Save a message."""
        query = """
        INSERT OR REPLACE INTO messages 
        (id, src, dst, type, priority, channel, timestamp, ack_required, 
         ack_id, data, retries, created_at, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            message.id,
            message.src,
            message.dst,
            message.type if isinstance(message.type, str) else message.type.value,
            message.pri if isinstance(message.pri, str) else message.pri.value,
            message.ch.value if message.ch else None,
            message.ts,
            1 if message.ack_required else 0,
            message.ack_id,
            json.dumps(message.data),
            message.retries,
            message.created_at.isoformat(),
            None,
        )
        await self._execute(query, params)
        logger.debug(f"Saved message: {message.id}")

    async def get(self, message_id: str) -> Message | None:
        """Get a message by ID."""
        row = await self._fetchone(
            "SELECT * FROM messages WHERE id = ?",
            (message_id,),
        )
        return self._row_to_message(row) if row else None

    async def get_by_source(
        self,
        source: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages from a source."""
        rows = await self._fetchall(
            "SELECT * FROM messages WHERE src = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (source, limit, offset),
        )
        return [self._row_to_message(row) for row in rows]

    async def get_by_destination(
        self,
        destination: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages to a destination."""
        rows = await self._fetchall(
            "SELECT * FROM messages WHERE dst = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (destination, limit, offset),
        )
        return [self._row_to_message(row) for row in rows]

    async def get_recent(self, limit: int = 100) -> list[Message]:
        """Get recent messages."""
        rows = await self._fetchall(
            "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_message(row) for row in rows]

    async def delete_older_than(self, days: int) -> int:
        """Delete messages older than N days."""
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_ts = int(cutoff.timestamp())

        if not self._db:
            return 0

        async with self._lock:
            cursor = await self._db.execute(
                "DELETE FROM messages WHERE timestamp < ?",
                (cutoff_ts,),
            )
            await self._db.commit()
            logger.info(f"Deleted {cursor.rowcount} old messages")
            return cursor.rowcount

    async def count(self) -> int:
        """Get total message count."""
        row = await self._fetchone("SELECT COUNT(*) as count FROM messages")
        return row["count"] if row else 0

    def _row_to_message(self, row: dict) -> Message:
        """Convert database row to Message."""
        return Message(
            id=row["id"],
            src=row["src"],
            dst=row["dst"],
            type=MessageType(row["type"]),
            pri=Priority(row["priority"]),
            ts=row["timestamp"],
            ack_required=bool(row["ack_required"]),
            ack_id=row["ack_id"],
            data=json.loads(row["data"]) if row["data"] else {},
            retries=row["retries"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


# =============================================================================
# Device Store
# =============================================================================


class DeviceStore(BaseStore):
    """Store for devices."""

    async def _init_schema(self) -> None:
        if self._db:
            await self._db.executescript(SCHEMA_DEVICES)
            await self._db.commit()

    async def save(self, device: Device) -> None:
        """Save or update a device."""
        query = """
        INSERT OR REPLACE INTO devices 
        (id, type, name, status, channels, preferred_channel, last_channel,
         last_seen, last_message_id, version, latitude, longitude, altitude,
         battery, uptime, capabilities, metadata, registered_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            device.id,
            device.type if isinstance(device.type, str) else device.type.value,
            device.name,
            device.status if isinstance(device.status, str) else device.status.value,
            json.dumps([c.value if hasattr(c, "value") else c for c in device.channels]),
            device.preferred_channel.value if device.preferred_channel else None,
            device.last_channel.value if device.last_channel else None,
            device.last_seen.isoformat() if device.last_seen else None,
            device.last_message_id,
            device.version,
            device.location.lat if device.location else None,
            device.location.lon if device.location else None,
            device.location.alt if device.location else None,
            device.battery,
            device.uptime,
            json.dumps(device.capabilities),
            json.dumps(device.metadata),
            device.registered_at.isoformat() if device.registered_at else None,
            device.created_at.isoformat(),
            datetime.now().isoformat(),
        )
        await self._execute(query, params)
        logger.debug(f"Saved device: {device.id}")

    async def get(self, device_id: str) -> Device | None:
        """Get a device by ID."""
        row = await self._fetchone(
            "SELECT * FROM devices WHERE id = ?",
            (device_id,),
        )
        return self._row_to_device(row) if row else None

    async def get_all(self) -> list[Device]:
        """Get all devices."""
        rows = await self._fetchall("SELECT * FROM devices ORDER BY last_seen DESC")
        return [self._row_to_device(row) for row in rows]

    async def get_by_status(self, status: DeviceStatus) -> list[Device]:
        """Get devices by status."""
        rows = await self._fetchall(
            "SELECT * FROM devices WHERE status = ?",
            (status.value,),
        )
        return [self._row_to_device(row) for row in rows]

    async def get_online(self) -> list[Device]:
        """Get online devices."""
        return await self.get_by_status(DeviceStatus.ONLINE)

    async def update_status(self, device_id: str, status: DeviceStatus) -> None:
        """Update device status."""
        await self._execute(
            "UPDATE devices SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, datetime.now().isoformat(), device_id),
        )

    async def update_last_seen(
        self,
        device_id: str,
        message_id: str | None = None,
    ) -> None:
        """Update device last seen timestamp."""
        now = datetime.now().isoformat()
        if message_id:
            await self._execute(
                "UPDATE devices SET last_seen = ?, last_message_id = ?, updated_at = ? WHERE id = ?",
                (now, message_id, now, device_id),
            )
        else:
            await self._execute(
                "UPDATE devices SET last_seen = ?, updated_at = ? WHERE id = ?",
                (now, now, device_id),
            )

    async def delete(self, device_id: str) -> bool:
        """Delete a device."""
        if not self._db:
            return False
        async with self._lock:
            cursor = await self._db.execute(
                "DELETE FROM devices WHERE id = ?",
                (device_id,),
            )
            await self._db.commit()
            return cursor.rowcount > 0

    async def count(self) -> int:
        """Get total device count."""
        row = await self._fetchone("SELECT COUNT(*) as count FROM devices")
        return row["count"] if row else 0

    def _row_to_device(self, row: dict) -> Device:
        """Convert database row to Device."""
        location = None
        if row["latitude"] is not None and row["longitude"] is not None:
            location = GPSLocation(
                lat=row["latitude"],
                lon=row["longitude"],
                alt=row["altitude"],
            )

        channels = json.loads(row["channels"]) if row["channels"] else []

        return Device(
            id=row["id"],
            type=DeviceType(row["type"]),
            name=row["name"],
            status=DeviceStatus(row["status"]),
            channels=channels,
            preferred_channel=row["preferred_channel"],
            last_channel=row["last_channel"],
            last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
            last_message_id=row["last_message_id"],
            version=row["version"],
            location=location,
            battery=row["battery"],
            uptime=row["uptime"],
            capabilities=json.loads(row["capabilities"]) if row["capabilities"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            registered_at=(
                datetime.fromisoformat(row["registered_at"])
                if row["registered_at"]
                else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


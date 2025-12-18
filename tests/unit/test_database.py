"""
Tests for database stores.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from nexus.domain.enums import DeviceStatus, DeviceType, MessageType, Priority
from nexus.domain.models import Device, GPSLocation, Message
from nexus.infrastructure.database import DeviceStore, MessageStore


class TestMessageStore:
    """Tests for MessageStore."""

    @pytest.mark.asyncio
    async def test_save_and_get(self, message_store: MessageStore) -> None:
        """Test saving and retrieving a message."""
        msg = Message(
            src="momo-001",
            dst="nexus",
            type=MessageType.STATUS,
            data={"battery": 85},
        )

        await message_store.save(msg)
        retrieved = await message_store.get(msg.id)

        assert retrieved is not None
        assert retrieved.id == msg.id
        assert retrieved.src == "momo-001"
        assert retrieved.data["battery"] == 85

    @pytest.mark.asyncio
    async def test_get_by_source(self, message_store: MessageStore) -> None:
        """Test getting messages by source."""
        msg1 = Message(src="momo-001", type=MessageType.STATUS)
        msg2 = Message(src="momo-001", type=MessageType.ALERT)
        msg3 = Message(src="momo-002", type=MessageType.STATUS)

        await message_store.save(msg1)
        await message_store.save(msg2)
        await message_store.save(msg3)

        messages = await message_store.get_by_source("momo-001")

        assert len(messages) == 2
        assert all(m.src == "momo-001" for m in messages)

    @pytest.mark.asyncio
    async def test_get_by_destination(self, message_store: MessageStore) -> None:
        """Test getting messages by destination."""
        msg1 = Message(src="nexus", dst="momo-001", type=MessageType.COMMAND)
        msg2 = Message(src="nexus", dst="momo-001", type=MessageType.CONFIG)
        msg3 = Message(src="nexus", dst="momo-002", type=MessageType.COMMAND)

        await message_store.save(msg1)
        await message_store.save(msg2)
        await message_store.save(msg3)

        messages = await message_store.get_by_destination("momo-001")

        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_get_recent(self, message_store: MessageStore) -> None:
        """Test getting recent messages."""
        for i in range(5):
            msg = Message(src=f"device-{i}", type=MessageType.STATUS)
            await message_store.save(msg)

        recent = await message_store.get_recent(limit=3)

        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_count(self, message_store: MessageStore) -> None:
        """Test counting messages."""
        for _ in range(3):
            msg = Message(src="test", type=MessageType.PING)
            await message_store.save(msg)

        count = await message_store.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_update_existing(self, message_store: MessageStore) -> None:
        """Test updating existing message."""
        msg = Message(
            src="momo-001",
            type=MessageType.STATUS,
            data={"version": 1},
        )
        await message_store.save(msg)

        # Update
        msg.data = {"version": 2}
        msg.retries = 1
        await message_store.save(msg)

        retrieved = await message_store.get(msg.id)
        assert retrieved is not None
        assert retrieved.data["version"] == 2
        assert retrieved.retries == 1


class TestDeviceStore:
    """Tests for DeviceStore."""

    @pytest.mark.asyncio
    async def test_save_and_get(self, device_store: DeviceStore) -> None:
        """Test saving and retrieving a device."""
        device = Device(
            id="momo-001",
            type=DeviceType.MOMO,
            name="Test MoMo",
            status=DeviceStatus.ONLINE,
        )

        await device_store.save(device)
        retrieved = await device_store.get("momo-001")

        assert retrieved is not None
        assert retrieved.id == "momo-001"
        assert retrieved.type == DeviceType.MOMO
        assert retrieved.name == "Test MoMo"

    @pytest.mark.asyncio
    async def test_get_all(self, device_store: DeviceStore) -> None:
        """Test getting all devices."""
        devices = [
            Device(id="momo-001", type=DeviceType.MOMO),
            Device(id="ghost-001", type=DeviceType.GHOSTBRIDGE),
            Device(id="mimic-001", type=DeviceType.MIMIC),
        ]

        for device in devices:
            await device_store.save(device)

        all_devices = await device_store.get_all()
        assert len(all_devices) == 3

    @pytest.mark.asyncio
    async def test_get_by_status(self, device_store: DeviceStore) -> None:
        """Test getting devices by status."""
        online = Device(id="online-1", status=DeviceStatus.ONLINE)
        offline = Device(id="offline-1", status=DeviceStatus.OFFLINE)

        await device_store.save(online)
        await device_store.save(offline)

        online_devices = await device_store.get_by_status(DeviceStatus.ONLINE)
        assert len(online_devices) == 1
        assert online_devices[0].id == "online-1"

    @pytest.mark.asyncio
    async def test_get_online(self, device_store: DeviceStore) -> None:
        """Test getting online devices."""
        await device_store.save(Device(id="on-1", status=DeviceStatus.ONLINE))
        await device_store.save(Device(id="off-1", status=DeviceStatus.OFFLINE))

        online = await device_store.get_online()
        assert len(online) == 1

    @pytest.mark.asyncio
    async def test_update_status(self, device_store: DeviceStore) -> None:
        """Test updating device status."""
        device = Device(id="momo-001", status=DeviceStatus.ONLINE)
        await device_store.save(device)

        await device_store.update_status("momo-001", DeviceStatus.OFFLINE)

        retrieved = await device_store.get("momo-001")
        assert retrieved is not None
        assert retrieved.status == DeviceStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_update_last_seen(self, device_store: DeviceStore) -> None:
        """Test updating last seen timestamp."""
        device = Device(id="momo-001")
        await device_store.save(device)

        await device_store.update_last_seen("momo-001", "msg-123")

        retrieved = await device_store.get("momo-001")
        assert retrieved is not None
        assert retrieved.last_seen is not None
        assert retrieved.last_message_id == "msg-123"

    @pytest.mark.asyncio
    async def test_delete(self, device_store: DeviceStore) -> None:
        """Test deleting a device."""
        device = Device(id="to-delete")
        await device_store.save(device)

        deleted = await device_store.delete("to-delete")
        assert deleted is True

        retrieved = await device_store.get("to-delete")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_device_with_location(self, device_store: DeviceStore) -> None:
        """Test device with GPS location."""
        device = Device(
            id="momo-001",
            location=GPSLocation(lat=41.0082, lon=28.9784, alt=50),
        )
        await device_store.save(device)

        retrieved = await device_store.get("momo-001")
        assert retrieved is not None
        assert retrieved.location is not None
        assert retrieved.location.lat == 41.0082

    @pytest.mark.asyncio
    async def test_count(self, device_store: DeviceStore) -> None:
        """Test counting devices."""
        for i in range(5):
            await device_store.save(Device(id=f"device-{i}"))

        count = await device_store.count()
        assert count == 5


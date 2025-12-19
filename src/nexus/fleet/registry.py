"""
Device Registry.

Manages device registration, lookup, and lifecycle.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime
from typing import Any

from nexus.config import NexusConfig, get_config
from nexus.core.events import EventBus, EventType, get_event_bus
from nexus.domain.enums import ChannelType, DeviceStatus, DeviceType
from nexus.domain.models import Device, GPSLocation, Message
from nexus.infrastructure.database import DeviceStore

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """
    Device registry for fleet management.

    Responsibilities:
    - Device registration and authentication
    - Device lookup and enumeration
    - Status tracking
    - Whitelist/blacklist enforcement
    """

    def __init__(
        self,
        config: NexusConfig | None = None,
        event_bus: EventBus | None = None,
        store: DeviceStore | None = None,
    ) -> None:
        self._config = config or get_config()
        self._event_bus = event_bus or get_event_bus()
        self._store = store

        # In-memory cache
        self._devices: dict[str, Device] = {}
        self._lock = asyncio.Lock()

        # Settings from config
        self._auto_register = self._config.fleet.auto_register
        self._whitelist = set(self._config.fleet.whitelist)
        self._blacklist = set(self._config.fleet.blacklist)

    # =========================================================================
    # Initialization
    # =========================================================================

    async def initialize(self, store: DeviceStore | None = None) -> None:
        """Initialize registry, load devices from database."""
        if store:
            self._store = store

        if self._store:
            devices = await self._store.get_all()
            async with self._lock:
                for device in devices:
                    self._devices[device.id] = device

            logger.info(f"Loaded {len(self._devices)} devices from database")

    # =========================================================================
    # Registration
    # =========================================================================

    async def register(
        self,
        device_id: str,
        device_type: DeviceType = DeviceType.UNKNOWN,
        name: str | None = None,
        channels: list[ChannelType] | None = None,
        version: str | None = None,
        capabilities: list[str] | None = None,
        location: GPSLocation | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Device | None:
        """
        Register a new device.

        Args:
            device_id: Unique device ID
            device_type: Type of device
            name: Human-readable name
            channels: Supported channels
            version: Device software version
            capabilities: Device capabilities
            location: GPS location
            metadata: Additional metadata

        Returns:
            Device if registered, None if rejected
        """
        # Check blacklist
        if device_id in self._blacklist:
            logger.warning(f"Device {device_id} is blacklisted, rejecting")
            return None

        # Check whitelist (if not empty)
        if self._whitelist and device_id not in self._whitelist and not self._auto_register:
            logger.warning(f"Device {device_id} not in whitelist, rejecting")
            return None

        # Check if already registered
        existing = await self.get(device_id)
        if existing:
            # Update existing device
            return await self.update(
                device_id,
                status=DeviceStatus.ONLINE,
                channels=channels,
                version=version,
                location=location,
                metadata=metadata,
            )

        # Create new device
        device = Device(
            id=device_id,
            type=device_type,
            name=name or device_id,
            status=DeviceStatus.ONLINE,
            channels=channels or [],
            version=version,
            capabilities=capabilities or [],
            location=location,
            metadata=metadata or {},
            registered_at=datetime.now(),
            last_seen=datetime.now(),
        )

        async with self._lock:
            self._devices[device_id] = device

        # Persist
        if self._store:
            await self._store.save(device)

        # Emit event
        await self._event_bus.emit(
            EventType.DEVICE_REGISTERED,
            {
                "device_id": device_id,
                "type": device_type.value if isinstance(device_type, DeviceType) else device_type,
                "name": device.name,
            },
        )

        logger.info(f"Registered device: {device_id} ({device_type})")
        return device

    async def register_from_hello(self, message: Message) -> Device | None:
        """
        Register device from HELLO message.

        Args:
            message: HELLO message from device

        Returns:
            Registered device or None
        """
        data = message.data

        # Extract device info from message
        device_type = DeviceType(data.get("type", "unknown"))
        channels = []
        for ch in data.get("channels", []):
            with contextlib.suppress(ValueError):
                channels.append(ChannelType(ch))

        location = None
        if "location" in data:
            loc = data["location"]
            location = GPSLocation(
                lat=loc.get("lat", 0),
                lon=loc.get("lon", 0),
                alt=loc.get("alt"),
            )

        return await self.register(
            device_id=message.src,
            device_type=device_type,
            name=data.get("name"),
            channels=channels,
            version=data.get("version"),
            capabilities=data.get("capabilities", []),
            location=location,
            metadata={
                "battery": data.get("battery"),
                "registered_via": message.ch.value if message.ch else "unknown",
            },
        )

    async def unregister(self, device_id: str) -> bool:
        """
        Unregister a device.

        Args:
            device_id: Device to unregister

        Returns:
            True if unregistered
        """
        async with self._lock:
            if device_id not in self._devices:
                return False

            del self._devices[device_id]

        if self._store:
            await self._store.delete(device_id)

        logger.info(f"Unregistered device: {device_id}")
        return True

    # =========================================================================
    # Lookup
    # =========================================================================

    async def get(self, device_id: str) -> Device | None:
        """Get device by ID."""
        async with self._lock:
            return self._devices.get(device_id)

    async def get_all(self) -> list[Device]:
        """Get all registered devices."""
        async with self._lock:
            return list(self._devices.values())

    async def get_by_type(self, device_type: DeviceType) -> list[Device]:
        """Get devices by type."""
        async with self._lock:
            return [d for d in self._devices.values() if d.type == device_type]

    async def get_by_status(self, status: DeviceStatus) -> list[Device]:
        """Get devices by status."""
        async with self._lock:
            return [d for d in self._devices.values() if d.status == status]

    async def get_online(self) -> list[Device]:
        """Get online devices."""
        return await self.get_by_status(DeviceStatus.ONLINE)

    async def get_by_channel(self, channel: ChannelType) -> list[Device]:
        """Get devices that support a specific channel."""
        async with self._lock:
            return [
                d for d in self._devices.values()
                if channel in d.channels or channel.value in d.channels
            ]

    async def exists(self, device_id: str) -> bool:
        """Check if device exists."""
        async with self._lock:
            return device_id in self._devices

    async def count(self) -> int:
        """Get total device count."""
        async with self._lock:
            return len(self._devices)

    # =========================================================================
    # Updates
    # =========================================================================

    async def update(
        self,
        device_id: str,
        status: DeviceStatus | None = None,
        channels: list[ChannelType] | None = None,
        version: str | None = None,
        location: GPSLocation | None = None,
        battery: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Device | None:
        """
        Update device information.

        Args:
            device_id: Device to update
            status: New status
            channels: Updated channels
            version: Updated version
            location: Updated location
            battery: Battery percentage
            metadata: Additional metadata to merge

        Returns:
            Updated device or None if not found
        """
        async with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return None

            if status:
                old_status = device.status
                device.status = status

                # Emit status change event
                if old_status != status:
                    event_type = {
                        DeviceStatus.ONLINE: EventType.DEVICE_ONLINE,
                        DeviceStatus.OFFLINE: EventType.DEVICE_OFFLINE,
                        DeviceStatus.LOST: EventType.DEVICE_LOST,
                    }.get(status, EventType.DEVICE_STATUS)

                    old_val = old_status.value if hasattr(old_status, "value") else str(old_status)
                    new_val = status.value if hasattr(status, "value") else str(status)

                    await self._event_bus.emit(
                        event_type,
                        {"device_id": device_id, "old_status": old_val, "new_status": new_val},
                    )

            if channels is not None:
                device.channels = channels

            if version:
                device.version = version

            if location:
                device.location = location

            if battery is not None:
                device.battery = battery

            if metadata:
                device.metadata.update(metadata)

            device.last_seen = datetime.now()

        # Persist
        if self._store:
            await self._store.save(device)

        return device

    async def update_last_seen(
        self,
        device_id: str,
        message_id: str | None = None,
        channel: ChannelType | None = None,
    ) -> None:
        """Update device last seen timestamp."""
        async with self._lock:
            device = self._devices.get(device_id)
            if device:
                device.last_seen = datetime.now()
                device.last_message_id = message_id
                if channel:
                    device.last_channel = channel

        if self._store:
            await self._store.update_last_seen(device_id, message_id)

    async def set_status(self, device_id: str, status: DeviceStatus) -> None:
        """Set device status."""
        await self.update(device_id, status=status)

    # =========================================================================
    # Whitelist/Blacklist
    # =========================================================================

    def add_to_whitelist(self, device_id: str) -> None:
        """Add device to whitelist."""
        self._whitelist.add(device_id)
        self._blacklist.discard(device_id)

    def remove_from_whitelist(self, device_id: str) -> None:
        """Remove device from whitelist."""
        self._whitelist.discard(device_id)

    def add_to_blacklist(self, device_id: str) -> None:
        """Add device to blacklist."""
        self._blacklist.add(device_id)
        self._whitelist.discard(device_id)

    def remove_from_blacklist(self, device_id: str) -> None:
        """Remove device from blacklist."""
        self._blacklist.discard(device_id)

    def is_allowed(self, device_id: str) -> bool:
        """Check if device is allowed to register."""
        if device_id in self._blacklist:
            return False
        if self._whitelist and device_id not in self._whitelist:
            return self._auto_register
        return True

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        async with self._lock:
            devices = list(self._devices.values())

        return {
            "total": len(devices),
            "online": sum(1 for d in devices if d.status == DeviceStatus.ONLINE),
            "offline": sum(1 for d in devices if d.status == DeviceStatus.OFFLINE),
            "sleeping": sum(1 for d in devices if d.status == DeviceStatus.SLEEPING),
            "lost": sum(1 for d in devices if d.status == DeviceStatus.LOST),
            "by_type": {
                t.value: sum(1 for d in devices if d.type == t)
                for t in DeviceType
                if sum(1 for d in devices if d.type == t) > 0
            },
        }


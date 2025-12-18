"""
Geo Manager.

Central orchestration for GPS tracking and geofencing.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List

from nexus.config import NexusConfig, get_config
from nexus.core.events import EventBus, EventType, get_event_bus
from nexus.geo.location import GPSCoordinate, Location, LocationFix
from nexus.geo.tracker import LocationTracker, TrackPoint
from nexus.geo.zones import Zone, CircleZone, PolygonZone, RectangleZone

logger = logging.getLogger(__name__)


class ZoneEventType(str, Enum):
    """Zone event types."""

    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"  # Stayed in zone for extended time


@dataclass
class ZoneEvent:
    """
    Zone crossing event.

    Attributes:
        device_id: Device that triggered event
        zone: Zone involved
        event_type: Enter, exit, or dwell
        location: Location when event occurred
        timestamp: When event occurred
        distance: Distance to zone center/boundary
    """

    device_id: str
    zone: Zone
    event_type: ZoneEventType
    location: Location
    timestamp: datetime = field(default_factory=datetime.now)
    distance: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "device_id": self.device_id,
            "zone_id": self.zone.id,
            "zone_name": self.zone.name,
            "event_type": self.event_type.value,
            "location": self.location.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "distance": self.distance,
        }


# Type alias for zone event handlers
ZoneEventHandler = Callable[[ZoneEvent], Coroutine[Any, Any, None]]


class GeoManager:
    """
    Central geo management.

    Responsibilities:
    - Device location tracking
    - Geofence zone management
    - Zone enter/exit detection
    - Event notification
    """

    def __init__(
        self,
        config: NexusConfig | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._config = config or get_config()
        self._event_bus = event_bus or get_event_bus()

        # Location tracker
        self._tracker = LocationTracker(
            max_history_per_device=self._config.geo.max_history,
            min_distance=self._config.geo.min_distance,
            max_accuracy=self._config.geo.max_accuracy,
        )

        # Zones
        self._zones: Dict[str, Zone] = {}
        self._zone_lock = asyncio.Lock()

        # Device zone state: device_id -> set of zone_ids currently in
        self._device_zones: Dict[str, set[str]] = {}

        # Zone event handlers
        self._handlers: List[ZoneEventHandler] = []

        self._running = False

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def tracker(self) -> LocationTracker:
        """Get location tracker."""
        return self._tracker

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> None:
        """Start geo manager."""
        if self._running:
            return

        self._running = True
        logger.info("Geo manager started")

    async def stop(self) -> None:
        """Stop geo manager."""
        self._running = False
        logger.info("Geo manager stopped")

    # =========================================================================
    # Location Updates
    # =========================================================================

    async def update_location(
        self,
        device_id: str,
        location: Location,
        accuracy: float | None = None,
        speed: float | None = None,
        heading: float | None = None,
        timestamp: datetime | None = None,
    ) -> List[ZoneEvent]:
        """
        Update device location and check geofences.

        Args:
            device_id: Device identifier
            location: New location
            accuracy: GPS accuracy
            speed: Speed in m/s
            heading: Heading in degrees
            timestamp: Fix timestamp

        Returns:
            List of zone events triggered
        """
        # Update tracker
        point = await self._tracker.update(
            device_id=device_id,
            location=location,
            accuracy=accuracy,
            speed=speed,
            heading=heading,
            timestamp=timestamp,
        )

        if not point:
            return []

        # Check geofences
        events = await self._check_geofences(device_id, location, timestamp)

        # Emit events
        for event in events:
            await self._emit_zone_event(event)

        return events

    async def update_from_message(
        self,
        device_id: str,
        data: dict[str, Any],
    ) -> List[ZoneEvent]:
        """
        Update location from message data.

        Args:
            device_id: Device identifier
            data: Location data from message

        Returns:
            List of zone events
        """
        # Parse location
        loc_data = data.get("location", data)

        location = Location(
            lat=loc_data.get("lat", 0),
            lon=loc_data.get("lon", 0),
            alt=loc_data.get("alt"),
        )

        return await self.update_location(
            device_id=device_id,
            location=location,
            accuracy=data.get("accuracy"),
            speed=data.get("speed"),
            heading=data.get("heading"),
        )

    # =========================================================================
    # Zone Management
    # =========================================================================

    async def add_zone(self, zone: Zone) -> None:
        """Add a geofence zone."""
        async with self._zone_lock:
            self._zones[zone.id] = zone
            logger.info(f"Added zone: {zone.name} ({zone.id})")

    async def remove_zone(self, zone_id: str) -> bool:
        """Remove a geofence zone."""
        async with self._zone_lock:
            if zone_id in self._zones:
                del self._zones[zone_id]
                logger.info(f"Removed zone: {zone_id}")
                return True
        return False

    async def get_zone(self, zone_id: str) -> Zone | None:
        """Get zone by ID."""
        async with self._zone_lock:
            return self._zones.get(zone_id)

    async def get_all_zones(self) -> List[Zone]:
        """Get all zones."""
        async with self._zone_lock:
            return list(self._zones.values())

    async def enable_zone(self, zone_id: str) -> bool:
        """Enable a zone."""
        async with self._zone_lock:
            zone = self._zones.get(zone_id)
            if zone:
                zone.enabled = True
                return True
        return False

    async def disable_zone(self, zone_id: str) -> bool:
        """Disable a zone."""
        async with self._zone_lock:
            zone = self._zones.get(zone_id)
            if zone:
                zone.enabled = False
                return True
        return False

    # =========================================================================
    # Geofence Checking
    # =========================================================================

    async def _check_geofences(
        self,
        device_id: str,
        location: Location,
        timestamp: datetime | None = None,
    ) -> List[ZoneEvent]:
        """Check all geofences for a device location."""
        events = []
        timestamp = timestamp or datetime.now()

        # Get current zone state
        if device_id not in self._device_zones:
            self._device_zones[device_id] = set()

        current_zones = self._device_zones[device_id]

        async with self._zone_lock:
            zones = list(self._zones.values())

        # Check each zone
        new_zones = set()
        for zone in zones:
            if not zone.enabled:
                continue

            is_inside = zone.contains(location)

            if is_inside:
                new_zones.add(zone.id)

                # Check for enter event
                if zone.id not in current_zones and zone.alert_on_enter:
                    events.append(
                        ZoneEvent(
                            device_id=device_id,
                            zone=zone,
                            event_type=ZoneEventType.ENTER,
                            location=location,
                            timestamp=timestamp,
                            distance=abs(zone.distance_to_boundary(location)),
                        )
                    )
            else:
                # Check for exit event
                if zone.id in current_zones and zone.alert_on_exit:
                    events.append(
                        ZoneEvent(
                            device_id=device_id,
                            zone=zone,
                            event_type=ZoneEventType.EXIT,
                            location=location,
                            timestamp=timestamp,
                            distance=abs(zone.distance_to_boundary(location)),
                        )
                    )

        # Update device zone state
        self._device_zones[device_id] = new_zones

        return events

    async def check_zones(
        self,
        location: GPSCoordinate,
    ) -> List[Zone]:
        """
        Check which zones contain a location.

        Args:
            location: Location to check

        Returns:
            List of zones containing the location
        """
        result = []

        async with self._zone_lock:
            for zone in self._zones.values():
                if zone.enabled and zone.contains(location):
                    result.append(zone)

        return result

    async def get_device_zones(self, device_id: str) -> List[Zone]:
        """Get zones a device is currently in."""
        zone_ids = self._device_zones.get(device_id, set())

        async with self._zone_lock:
            return [
                self._zones[zone_id]
                for zone_id in zone_ids
                if zone_id in self._zones
            ]

    # =========================================================================
    # Event Handling
    # =========================================================================

    def add_handler(self, handler: ZoneEventHandler) -> None:
        """Add zone event handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: ZoneEventHandler) -> None:
        """Remove zone event handler."""
        try:
            self._handlers.remove(handler)
        except ValueError:
            pass

    async def _emit_zone_event(self, event: ZoneEvent) -> None:
        """Emit zone event to handlers and event bus."""
        # Call handlers
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Zone event handler error: {e}")

        # Emit to event bus
        event_type = {
            ZoneEventType.ENTER: EventType.ZONE_ENTER,
            ZoneEventType.EXIT: EventType.ZONE_EXIT,
        }.get(event.event_type, EventType.ZONE_ENTER)

        await self._event_bus.emit(event_type, event.to_dict())

        logger.info(
            f"Zone {event.event_type.value}: {event.device_id} "
            f"{'entered' if event.event_type == ZoneEventType.ENTER else 'exited'} "
            f"{event.zone.name}"
        )

    # =========================================================================
    # Queries
    # =========================================================================

    async def get_location(self, device_id: str) -> TrackPoint | None:
        """Get current device location."""
        return await self._tracker.get_current(device_id)

    async def get_all_locations(self) -> Dict[str, TrackPoint]:
        """Get all device locations."""
        return await self._tracker.get_all_current()

    async def get_nearby(
        self,
        location: GPSCoordinate,
        radius: float,
    ) -> List[tuple[str, TrackPoint, float]]:
        """Find devices near a location."""
        return await self._tracker.get_nearby_devices(location, radius)

    async def get_devices_in_zone(self, zone_id: str) -> List[str]:
        """Get devices currently in a zone."""
        return [
            device_id
            for device_id, zones in self._device_zones.items()
            if zone_id in zones
        ]

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get geo manager statistics."""
        tracker_stats = await self._tracker.get_stats()

        async with self._zone_lock:
            zone_count = len(self._zones)
            enabled_zones = sum(1 for z in self._zones.values() if z.enabled)

        return {
            "running": self._running,
            "zones": {
                "total": zone_count,
                "enabled": enabled_zones,
            },
            "tracker": tracker_stats,
            "devices_with_zone_state": len(self._device_zones),
        }


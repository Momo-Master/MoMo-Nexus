"""
Location tracking.

Tracks device locations with history and filtering.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nexus.geo.location import (
    GPSCoordinate,
    Location,
    LocationFix,
    bearing,
    distance_haversine,
)

logger = logging.getLogger(__name__)


@dataclass
class TrackPoint:
    """
    A point in a device's track history.

    Attributes:
        device_id: Device identifier
        location: Location fix
        timestamp: When recorded
        speed: Speed in m/s
        heading: Heading in degrees
        accuracy: GPS accuracy in meters
    """

    device_id: str
    location: Location
    timestamp: datetime = field(default_factory=datetime.now)
    speed: float | None = None
    heading: float | None = None
    accuracy: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "device_id": self.device_id,
            "location": self.location.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "speed": self.speed,
            "heading": self.heading,
            "accuracy": self.accuracy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrackPoint:
        """Deserialize from dictionary."""
        return cls(
            device_id=data["device_id"],
            location=Location.from_dict(data["location"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            speed=data.get("speed"),
            heading=data.get("heading"),
            accuracy=data.get("accuracy"),
        )


@dataclass
class DeviceTrack:
    """
    Track history for a device.

    Attributes:
        device_id: Device identifier
        history: Deque of track points
        max_points: Maximum points to keep
        current: Current location
        total_distance: Total distance traveled (meters)
    """

    device_id: str
    max_points: int = 1000
    history: deque[TrackPoint] = field(default_factory=lambda: deque(maxlen=1000))
    current: TrackPoint | None = None
    total_distance: float = 0.0

    def __post_init__(self) -> None:
        """Initialize history with correct max length."""
        if not isinstance(self.history, deque):
            self.history = deque(self.history, maxlen=self.max_points)

    def add_point(self, point: TrackPoint) -> None:
        """Add a track point."""
        # Calculate distance from previous point
        if self.current:
            dist = distance_haversine(
                self.current.location,
                point.location,
            )
            self.total_distance += dist

            # Calculate speed if not provided
            if point.speed is None:
                time_delta = (point.timestamp - self.current.timestamp).total_seconds()
                if time_delta > 0:
                    point.speed = dist / time_delta

            # Calculate heading if not provided
            if point.heading is None:
                point.heading = bearing(self.current.location, point.location)

        self.history.append(point)
        self.current = point

    @property
    def last_update(self) -> datetime | None:
        """Get last update time."""
        if self.current:
            return self.current.timestamp
        return None

    def get_recent(self, count: int = 10) -> list[TrackPoint]:
        """Get recent track points."""
        return list(self.history)[-count:]

    def get_since(self, since: datetime) -> list[TrackPoint]:
        """Get track points since a timestamp."""
        return [p for p in self.history if p.timestamp >= since]

    def get_distance_since(self, since: datetime) -> float:
        """Calculate distance traveled since a timestamp."""
        points = self.get_since(since)
        if len(points) < 2:
            return 0.0

        total = 0.0
        for i in range(1, len(points)):
            total += distance_haversine(
                points[i - 1].location,
                points[i].location,
            )
        return total

    def clear(self) -> None:
        """Clear track history."""
        self.history.clear()
        self.current = None
        self.total_distance = 0.0


class LocationTracker:
    """
    Tracks locations for multiple devices.

    Features:
    - Per-device track history
    - Speed and heading calculation
    - Distance filtering (ignore small movements)
    - Statistics
    """

    def __init__(
        self,
        max_history_per_device: int = 1000,
        min_distance: float = 5.0,  # Minimum movement in meters
        max_accuracy: float = 100.0,  # Maximum acceptable accuracy
    ) -> None:
        """
        Initialize location tracker.

        Args:
            max_history_per_device: Max points per device
            min_distance: Minimum distance for new point
            max_accuracy: Maximum acceptable accuracy
        """
        self._max_history = max_history_per_device
        self._min_distance = min_distance
        self._max_accuracy = max_accuracy

        self._tracks: dict[str, DeviceTrack] = {}
        self._lock = asyncio.Lock()

    # =========================================================================
    # Location Updates
    # =========================================================================

    async def update(
        self,
        device_id: str,
        location: Location,
        accuracy: float | None = None,
        speed: float | None = None,
        heading: float | None = None,
        timestamp: datetime | None = None,
    ) -> TrackPoint | None:
        """
        Update device location.

        Args:
            device_id: Device identifier
            location: New location
            accuracy: GPS accuracy
            speed: Speed in m/s
            heading: Heading in degrees
            timestamp: Fix timestamp

        Returns:
            TrackPoint if accepted, None if filtered
        """
        # Filter by accuracy
        if accuracy is not None and accuracy > self._max_accuracy:
            logger.debug(f"Ignoring low accuracy fix: {accuracy}m")
            return None

        timestamp = timestamp or datetime.now()

        async with self._lock:
            # Get or create track
            if device_id not in self._tracks:
                self._tracks[device_id] = DeviceTrack(
                    device_id=device_id,
                    max_points=self._max_history,
                )

            track = self._tracks[device_id]

            # Filter by minimum distance
            if track.current:
                dist = distance_haversine(track.current.location, location)
                if dist < self._min_distance:
                    logger.debug(f"Ignoring small movement: {dist:.1f}m")
                    return None

            # Create track point
            point = TrackPoint(
                device_id=device_id,
                location=location,
                timestamp=timestamp,
                speed=speed,
                heading=heading,
                accuracy=accuracy,
            )

            track.add_point(point)
            logger.debug(f"Location update: {device_id} @ {location}")

            return point

    async def update_from_fix(
        self,
        device_id: str,
        fix: LocationFix,
    ) -> TrackPoint | None:
        """Update from a LocationFix object."""
        return await self.update(
            device_id=device_id,
            location=fix.location,
            accuracy=fix.accuracy,
            speed=fix.speed,
            heading=fix.heading,
            timestamp=fix.timestamp,
        )

    # =========================================================================
    # Queries
    # =========================================================================

    async def get_current(self, device_id: str) -> TrackPoint | None:
        """Get current location for device."""
        async with self._lock:
            track = self._tracks.get(device_id)
            if track:
                return track.current
        return None

    async def get_all_current(self) -> dict[str, TrackPoint]:
        """Get current locations for all devices."""
        async with self._lock:
            return {
                device_id: track.current
                for device_id, track in self._tracks.items()
                if track.current
            }

    async def get_history(
        self,
        device_id: str,
        count: int | None = None,
        since: datetime | None = None,
    ) -> list[TrackPoint]:
        """
        Get track history for device.

        Args:
            device_id: Device identifier
            count: Max points to return
            since: Get points since timestamp

        Returns:
            List of track points
        """
        async with self._lock:
            track = self._tracks.get(device_id)
            if not track:
                return []

            points = track.get_since(since) if since else list(track.history)

            if count:
                points = points[-count:]

            return points

    async def get_distance(
        self,
        device_id: str,
        since: datetime | None = None,
    ) -> float:
        """Get total distance traveled."""
        async with self._lock:
            track = self._tracks.get(device_id)
            if not track:
                return 0.0

            if since:
                return track.get_distance_since(since)
            return track.total_distance

    async def get_nearby_devices(
        self,
        location: GPSCoordinate,
        radius: float,
    ) -> list[tuple[str, TrackPoint, float]]:
        """
        Find devices near a location.

        Args:
            location: Center point
            radius: Radius in meters

        Returns:
            List of (device_id, track_point, distance) tuples
        """
        result = []

        async with self._lock:
            for device_id, track in self._tracks.items():
                if track.current:
                    dist = distance_haversine(location, track.current.location)
                    if dist <= radius:
                        result.append((device_id, track.current, dist))

        # Sort by distance
        result.sort(key=lambda x: x[2])
        return result

    # =========================================================================
    # Management
    # =========================================================================

    async def clear_device(self, device_id: str) -> None:
        """Clear history for a device."""
        async with self._lock:
            if device_id in self._tracks:
                self._tracks[device_id].clear()

    async def remove_device(self, device_id: str) -> None:
        """Remove device from tracker."""
        async with self._lock:
            self._tracks.pop(device_id, None)

    async def clear_all(self) -> None:
        """Clear all tracking data."""
        async with self._lock:
            self._tracks.clear()

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get tracker statistics."""
        async with self._lock:
            device_count = len(self._tracks)
            total_points = sum(len(t.history) for t in self._tracks.values())
            total_distance = sum(t.total_distance for t in self._tracks.values())

            # Find most active
            most_active = None
            max_points = 0
            for device_id, track in self._tracks.items():
                if len(track.history) > max_points:
                    max_points = len(track.history)
                    most_active = device_id

            return {
                "devices_tracked": device_count,
                "total_points": total_points,
                "total_distance_km": total_distance / 1000,
                "most_active_device": most_active,
                "max_history_per_device": self._max_history,
                "min_distance_filter": self._min_distance,
            }


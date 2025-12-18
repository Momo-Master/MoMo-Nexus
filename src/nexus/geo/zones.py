"""
Geofencing zones.

Supports circle, polygon, and rectangle zone types.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Tuple

from nexus.geo.location import GPSCoordinate, distance_haversine


class ZoneType(str, Enum):
    """Zone geometry type."""

    CIRCLE = "circle"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"


@dataclass
class Zone(ABC):
    """
    Abstract base class for geofence zones.

    Attributes:
        id: Unique zone identifier
        name: Human-readable name
        zone_type: Type of zone geometry
        enabled: Whether zone is active
        metadata: Additional zone metadata
    """

    id: str
    name: str
    zone_type: ZoneType
    enabled: bool = True
    alert_on_enter: bool = True
    alert_on_exit: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def contains(self, point: GPSCoordinate) -> bool:
        """Check if point is inside the zone."""
        pass

    @abstractmethod
    def distance_to_boundary(self, point: GPSCoordinate) -> float:
        """
        Calculate distance to zone boundary.

        Returns:
            Positive value if outside, negative if inside
        """
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize zone to dictionary."""
        pass

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Zone":
        """Deserialize zone from dictionary."""
        zone_type = ZoneType(data["zone_type"])

        if zone_type == ZoneType.CIRCLE:
            return CircleZone.from_dict(data)
        elif zone_type == ZoneType.POLYGON:
            return PolygonZone.from_dict(data)
        elif zone_type == ZoneType.RECTANGLE:
            return RectangleZone.from_dict(data)
        else:
            raise ValueError(f"Unknown zone type: {zone_type}")


@dataclass
class CircleZone(Zone):
    """
    Circular geofence zone.

    Attributes:
        center: Circle center point
        radius: Radius in meters
    """

    center: GPSCoordinate = field(default_factory=lambda: GPSCoordinate(0, 0))
    radius: float = 100.0  # meters

    def __post_init__(self) -> None:
        """Set zone type."""
        object.__setattr__(self, "zone_type", ZoneType.CIRCLE)

    def contains(self, point: GPSCoordinate) -> bool:
        """Check if point is inside the circle."""
        distance = distance_haversine(self.center, point)
        return distance <= self.radius

    def distance_to_boundary(self, point: GPSCoordinate) -> float:
        """Distance to circle boundary (positive = outside)."""
        distance = distance_haversine(self.center, point)
        return distance - self.radius

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "zone_type": self.zone_type.value,
            "enabled": self.enabled,
            "alert_on_enter": self.alert_on_enter,
            "alert_on_exit": self.alert_on_exit,
            "center": self.center.to_dict(),
            "radius": self.radius,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CircleZone":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            zone_type=ZoneType.CIRCLE,
            enabled=data.get("enabled", True),
            alert_on_enter=data.get("alert_on_enter", True),
            alert_on_exit=data.get("alert_on_exit", True),
            center=GPSCoordinate.from_dict(data["center"]),
            radius=data["radius"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class PolygonZone(Zone):
    """
    Polygon geofence zone.

    Attributes:
        vertices: List of polygon vertices (must be >= 3)
    """

    vertices: List[GPSCoordinate] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set zone type and validate."""
        object.__setattr__(self, "zone_type", ZoneType.POLYGON)
        if len(self.vertices) < 3:
            raise ValueError("Polygon must have at least 3 vertices")

    def contains(self, point: GPSCoordinate) -> bool:
        """
        Check if point is inside the polygon.

        Uses ray casting algorithm.
        """
        n = len(self.vertices)
        inside = False

        j = n - 1
        for i in range(n):
            vi = self.vertices[i]
            vj = self.vertices[j]

            if (
                (vi.lat > point.lat) != (vj.lat > point.lat)
                and point.lon
                < (vj.lon - vi.lon) * (point.lat - vi.lat) / (vj.lat - vi.lat) + vi.lon
            ):
                inside = not inside

            j = i

        return inside

    def distance_to_boundary(self, point: GPSCoordinate) -> float:
        """
        Distance to polygon boundary.

        Returns minimum distance to any edge.
        Positive if outside, negative if inside.
        """
        min_dist = float("inf")
        n = len(self.vertices)

        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]

            # Distance to edge
            dist = self._point_to_segment_distance(point, v1, v2)
            min_dist = min(min_dist, dist)

        # Negate if inside
        if self.contains(point):
            return -min_dist

        return min_dist

    def _point_to_segment_distance(
        self,
        point: GPSCoordinate,
        v1: GPSCoordinate,
        v2: GPSCoordinate,
    ) -> float:
        """Calculate distance from point to line segment."""
        # Convert to simple 2D for approximation
        px, py = point.lon, point.lat
        x1, y1 = v1.lon, v1.lat
        x2, y2 = v2.lon, v2.lat

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return distance_haversine(point, v1)

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        closest = GPSCoordinate(lat=y1 + t * dy, lon=x1 + t * dx)
        return distance_haversine(point, closest)

    @property
    def centroid(self) -> GPSCoordinate:
        """Calculate polygon centroid."""
        lat_sum = sum(v.lat for v in self.vertices)
        lon_sum = sum(v.lon for v in self.vertices)
        n = len(self.vertices)
        return GPSCoordinate(lat=lat_sum / n, lon=lon_sum / n)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "zone_type": self.zone_type.value,
            "enabled": self.enabled,
            "alert_on_enter": self.alert_on_enter,
            "alert_on_exit": self.alert_on_exit,
            "vertices": [v.to_dict() for v in self.vertices],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolygonZone":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            zone_type=ZoneType.POLYGON,
            enabled=data.get("enabled", True),
            alert_on_enter=data.get("alert_on_enter", True),
            alert_on_exit=data.get("alert_on_exit", True),
            vertices=[GPSCoordinate.from_dict(v) for v in data["vertices"]],
            metadata=data.get("metadata", {}),
        )


@dataclass
class RectangleZone(Zone):
    """
    Rectangle geofence zone (axis-aligned).

    Attributes:
        southwest: Southwest corner
        northeast: Northeast corner
    """

    southwest: GPSCoordinate = field(default_factory=lambda: GPSCoordinate(0, 0))
    northeast: GPSCoordinate = field(default_factory=lambda: GPSCoordinate(0, 0))

    def __post_init__(self) -> None:
        """Set zone type and validate."""
        object.__setattr__(self, "zone_type", ZoneType.RECTANGLE)
        if self.southwest.lat >= self.northeast.lat:
            raise ValueError("Southwest latitude must be less than northeast")
        if self.southwest.lon >= self.northeast.lon:
            raise ValueError("Southwest longitude must be less than northeast")

    def contains(self, point: GPSCoordinate) -> bool:
        """Check if point is inside the rectangle."""
        return (
            self.southwest.lat <= point.lat <= self.northeast.lat
            and self.southwest.lon <= point.lon <= self.northeast.lon
        )

    def distance_to_boundary(self, point: GPSCoordinate) -> float:
        """Distance to rectangle boundary."""
        # Clamp point to rectangle
        clamped_lat = max(self.southwest.lat, min(point.lat, self.northeast.lat))
        clamped_lon = max(self.southwest.lon, min(point.lon, self.northeast.lon))
        clamped = GPSCoordinate(lat=clamped_lat, lon=clamped_lon)

        dist = distance_haversine(point, clamped)

        if self.contains(point):
            # Calculate distance to nearest edge
            to_south = distance_haversine(point, GPSCoordinate(self.southwest.lat, point.lon))
            to_north = distance_haversine(point, GPSCoordinate(self.northeast.lat, point.lon))
            to_west = distance_haversine(point, GPSCoordinate(point.lat, self.southwest.lon))
            to_east = distance_haversine(point, GPSCoordinate(point.lat, self.northeast.lon))
            return -min(to_south, to_north, to_west, to_east)

        return dist

    @property
    def center(self) -> GPSCoordinate:
        """Calculate rectangle center."""
        return GPSCoordinate(
            lat=(self.southwest.lat + self.northeast.lat) / 2,
            lon=(self.southwest.lon + self.northeast.lon) / 2,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "zone_type": self.zone_type.value,
            "enabled": self.enabled,
            "alert_on_enter": self.alert_on_enter,
            "alert_on_exit": self.alert_on_exit,
            "southwest": self.southwest.to_dict(),
            "northeast": self.northeast.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RectangleZone":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            zone_type=ZoneType.RECTANGLE,
            enabled=data.get("enabled", True),
            alert_on_enter=data.get("alert_on_enter", True),
            alert_on_exit=data.get("alert_on_exit", True),
            southwest=GPSCoordinate.from_dict(data["southwest"]),
            northeast=GPSCoordinate.from_dict(data["northeast"]),
            metadata=data.get("metadata", {}),
        )


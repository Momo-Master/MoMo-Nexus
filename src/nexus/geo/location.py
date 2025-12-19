"""
GPS location models and calculations.

Implements geodesic calculations using the Haversine formula.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Earth's radius in meters
EARTH_RADIUS = 6371000


@dataclass
class GPSCoordinate:
    """
    GPS coordinate (latitude, longitude).

    Attributes:
        lat: Latitude in decimal degrees (-90 to 90)
        lon: Longitude in decimal degrees (-180 to 180)
    """

    lat: float
    lon: float

    def __post_init__(self) -> None:
        """Validate coordinates."""
        if not -90 <= self.lat <= 90:
            raise ValueError(f"Latitude must be between -90 and 90: {self.lat}")
        if not -180 <= self.lon <= 180:
            raise ValueError(f"Longitude must be between -180 and 180: {self.lon}")

    def to_tuple(self) -> tuple[float, float]:
        """Convert to (lat, lon) tuple."""
        return (self.lat, self.lon)

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {"lat": self.lat, "lon": self.lon}

    @classmethod
    def from_tuple(cls, coords: tuple[float, float]) -> GPSCoordinate:
        """Create from (lat, lon) tuple."""
        return cls(lat=coords[0], lon=coords[1])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GPSCoordinate:
        """Create from dictionary."""
        return cls(lat=data["lat"], lon=data["lon"])

    def distance_to(self, other: GPSCoordinate) -> float:
        """
        Calculate distance to another coordinate in meters.

        Uses the Haversine formula.
        """
        return distance_haversine(self, other)

    def bearing_to(self, other: GPSCoordinate) -> float:
        """
        Calculate initial bearing to another coordinate.

        Returns bearing in degrees (0-360, 0 = North).
        """
        return bearing(self, other)

    def destination(self, distance: float, bearing_deg: float) -> GPSCoordinate:
        """
        Calculate destination point given distance and bearing.

        Args:
            distance: Distance in meters
            bearing_deg: Bearing in degrees

        Returns:
            Destination coordinate
        """
        return destination_point(self, distance, bearing_deg)

    def __str__(self) -> str:
        """String representation."""
        ns = "N" if self.lat >= 0 else "S"
        ew = "E" if self.lon >= 0 else "W"
        return f"{abs(self.lat):.6f}°{ns}, {abs(self.lon):.6f}°{ew}"


@dataclass
class Location(GPSCoordinate):
    """
    Location with altitude.

    Attributes:
        lat: Latitude
        lon: Longitude
        alt: Altitude in meters (optional)
    """

    alt: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = super().to_dict()
        if self.alt is not None:
            d["alt"] = self.alt
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Location:
        """Create from dictionary."""
        return cls(
            lat=data["lat"],
            lon=data["lon"],
            alt=data.get("alt"),
        )


@dataclass
class LocationFix:
    """
    Complete location fix with metadata.

    Attributes:
        location: GPS location
        timestamp: Fix timestamp
        accuracy: Horizontal accuracy in meters
        altitude_accuracy: Vertical accuracy in meters
        speed: Speed in m/s
        heading: Heading in degrees
        source: Fix source (gps, network, etc.)
    """

    location: Location
    timestamp: datetime = field(default_factory=datetime.now)
    accuracy: float | None = None
    altitude_accuracy: float | None = None
    speed: float | None = None
    heading: float | None = None
    source: str = "gps"

    @property
    def lat(self) -> float:
        """Latitude shortcut."""
        return self.location.lat

    @property
    def lon(self) -> float:
        """Longitude shortcut."""
        return self.location.lon

    @property
    def alt(self) -> float | None:
        """Altitude shortcut."""
        return self.location.alt

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "location": self.location.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "accuracy": self.accuracy,
            "altitude_accuracy": self.altitude_accuracy,
            "speed": self.speed,
            "heading": self.heading,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LocationFix:
        """Create from dictionary."""
        return cls(
            location=Location.from_dict(data["location"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            accuracy=data.get("accuracy"),
            altitude_accuracy=data.get("altitude_accuracy"),
            speed=data.get("speed"),
            heading=data.get("heading"),
            source=data.get("source", "gps"),
        )


# =============================================================================
# Geodesic Calculations
# =============================================================================


def distance_haversine(p1: GPSCoordinate, p2: GPSCoordinate) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        p1: First coordinate
        p2: Second coordinate

    Returns:
        Distance in meters
    """
    lat1 = math.radians(p1.lat)
    lat2 = math.radians(p2.lat)
    delta_lat = math.radians(p2.lat - p1.lat)
    delta_lon = math.radians(p2.lon - p1.lon)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS * c


def bearing(p1: GPSCoordinate, p2: GPSCoordinate) -> float:
    """
    Calculate initial bearing from p1 to p2.

    Args:
        p1: Start coordinate
        p2: End coordinate

    Returns:
        Bearing in degrees (0-360, 0 = North)
    """
    lat1 = math.radians(p1.lat)
    lat2 = math.radians(p2.lat)
    delta_lon = math.radians(p2.lon - p1.lon)

    x = math.sin(delta_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)

    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)

    return (bearing_deg + 360) % 360


def destination_point(
    start: GPSCoordinate,
    distance: float,
    bearing_deg: float,
) -> GPSCoordinate:
    """
    Calculate destination point given start, distance and bearing.

    Args:
        start: Start coordinate
        distance: Distance in meters
        bearing_deg: Bearing in degrees

    Returns:
        Destination coordinate
    """
    lat1 = math.radians(start.lat)
    lon1 = math.radians(start.lon)
    bearing_rad = math.radians(bearing_deg)

    angular_dist = distance / EARTH_RADIUS

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_dist)
        + math.cos(lat1) * math.sin(angular_dist) * math.cos(bearing_rad)
    )

    lon2 = lon1 + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_dist) * math.cos(lat1),
        math.cos(angular_dist) - math.sin(lat1) * math.sin(lat2),
    )

    return GPSCoordinate(
        lat=math.degrees(lat2),
        lon=math.degrees(lon2),
    )


def midpoint(p1: GPSCoordinate, p2: GPSCoordinate) -> GPSCoordinate:
    """
    Calculate midpoint between two coordinates.

    Args:
        p1: First coordinate
        p2: Second coordinate

    Returns:
        Midpoint coordinate
    """
    lat1 = math.radians(p1.lat)
    lon1 = math.radians(p1.lon)
    lat2 = math.radians(p2.lat)
    delta_lon = math.radians(p2.lon - p1.lon)

    bx = math.cos(lat2) * math.cos(delta_lon)
    by = math.cos(lat2) * math.sin(delta_lon)

    lat3 = math.atan2(
        math.sin(lat1) + math.sin(lat2),
        math.sqrt((math.cos(lat1) + bx) ** 2 + by ** 2),
    )
    lon3 = lon1 + math.atan2(by, math.cos(lat1) + bx)

    return GPSCoordinate(
        lat=math.degrees(lat3),
        lon=math.degrees(lon3),
    )


def bounding_box(
    center: GPSCoordinate,
    radius: float,
) -> tuple[GPSCoordinate, GPSCoordinate]:
    """
    Calculate bounding box for a circle.

    Args:
        center: Circle center
        radius: Radius in meters

    Returns:
        Tuple of (southwest, northeast) corners
    """
    # Approximate degree per meter
    lat_delta = radius / 111320
    lon_delta = radius / (111320 * math.cos(math.radians(center.lat)))

    sw = GPSCoordinate(
        lat=center.lat - lat_delta,
        lon=center.lon - lon_delta,
    )
    ne = GPSCoordinate(
        lat=center.lat + lat_delta,
        lon=center.lon + lon_delta,
    )

    return sw, ne


def format_distance(meters: float) -> str:
    """Format distance for display."""
    if meters < 1000:
        return f"{meters:.0f}m"
    else:
        return f"{meters/1000:.2f}km"


def format_bearing(degrees: float) -> str:
    """Format bearing as compass direction."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % 8
    return directions[index]


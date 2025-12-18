"""Domain models for MoMo-Nexus."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from nexus.domain.enums import (
    ChannelStatus,
    ChannelType,
    DeviceStatus,
    DeviceType,
    MessageType,
    Priority,
)


def generate_id() -> str:
    """Generate a unique message/command ID."""
    return uuid.uuid4().hex[:12]


def now_timestamp() -> int:
    """Get current Unix timestamp."""
    return int(datetime.now().timestamp())


class GPSLocation(BaseModel):
    """GPS location data."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    alt: float | None = Field(default=None, description="Altitude in meters")
    accuracy: float | None = Field(default=None, description="Accuracy in meters")
    timestamp: int | None = Field(default=None, description="GPS fix timestamp")

    def to_tuple(self) -> tuple[float, float]:
        """Return as (lat, lon) tuple."""
        return (self.lat, self.lon)


class Message(BaseModel):
    """
    Core message model for all communication.

    Used for device-to-nexus, nexus-to-device, and internal routing.
    """

    # Required fields
    v: int = Field(default=1, description="Protocol version")
    id: str = Field(default_factory=generate_id, description="Unique message ID")
    src: str = Field(..., description="Source device ID")
    type: MessageType = Field(..., description="Message type")

    # Optional routing fields
    dst: str | None = Field(default=None, description="Destination device ID (None=broadcast)")
    ts: int = Field(default_factory=now_timestamp, description="Unix timestamp")
    ch: ChannelType | None = Field(default=None, description="Channel received on")
    pri: Priority = Field(default=Priority.NORMAL, description="Message priority")

    # Acknowledgment
    ack_required: bool = Field(default=False, description="Sender expects ACK")
    ack_id: str | None = Field(default=None, description="ID of message being ACKed")

    # Payload
    data: dict[str, Any] = Field(default_factory=dict, description="Message payload")

    # Metadata (internal use)
    retries: int = Field(default=0, description="Number of send retries")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True

    def needs_ack(self) -> bool:
        """Check if this message requires acknowledgment."""
        return self.ack_required and self.type not in (MessageType.ACK, MessageType.NACK)

    def create_ack(self, success: bool = True) -> "Message":
        """Create an ACK/NACK response for this message."""
        return Message(
            src="nexus",
            dst=self.src,
            type=MessageType.ACK if success else MessageType.NACK,
            ack_id=self.id,
            pri=self.pri,
        )


class Device(BaseModel):
    """Registered device in the fleet."""

    id: str = Field(..., description="Unique device ID (e.g., 'momo-001')")
    type: DeviceType = Field(default=DeviceType.UNKNOWN, description="Device type")
    name: str | None = Field(default=None, description="Human-readable name")
    status: DeviceStatus = Field(default=DeviceStatus.UNREGISTERED)

    # Connection info
    channels: list[ChannelType] = Field(default_factory=list, description="Supported channels")
    preferred_channel: ChannelType | None = Field(default=None)
    last_channel: ChannelType | None = Field(default=None, description="Last used channel")

    # Status
    last_seen: datetime | None = Field(default=None)
    last_message_id: str | None = Field(default=None)

    # Device info
    version: str | None = Field(default=None, description="Device software version")
    location: GPSLocation | None = Field(default=None)
    battery: int | None = Field(default=None, ge=0, le=100, description="Battery percentage")
    uptime: int | None = Field(default=None, description="Uptime in seconds")

    # Metadata
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    registered_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True

    def is_online(self) -> bool:
        """Check if device is online."""
        return self.status == DeviceStatus.ONLINE

    def is_reachable(self) -> bool:
        """Check if device might be reachable."""
        return self.status in (DeviceStatus.ONLINE, DeviceStatus.SLEEPING)


class ChannelMetrics(BaseModel):
    """Metrics for a communication channel."""

    latency_ms: float = Field(default=0, ge=0, description="Average latency in ms")
    bandwidth_kbps: float = Field(default=0, ge=0, description="Bandwidth in kbps")
    packet_loss: float = Field(default=0, ge=0, le=100, description="Packet loss percentage")
    messages_sent: int = Field(default=0, ge=0)
    messages_received: int = Field(default=0, ge=0)
    bytes_sent: int = Field(default=0, ge=0)
    bytes_received: int = Field(default=0, ge=0)
    last_success: datetime | None = Field(default=None)
    last_failure: datetime | None = Field(default=None)
    consecutive_failures: int = Field(default=0, ge=0)


class Channel(BaseModel):
    """Communication channel information."""

    name: str = Field(..., description="Channel name (unique)")
    type: ChannelType = Field(..., description="Channel type")
    status: ChannelStatus = Field(default=ChannelStatus.UNKNOWN)
    enabled: bool = Field(default=True)

    # Performance characteristics
    typical_latency_ms: int = Field(default=1000, description="Typical latency")
    max_payload_bytes: int = Field(default=200, description="Max message size")
    cost_per_kb: float = Field(default=0, description="Cost per KB (for prioritization)")

    # Health
    metrics: ChannelMetrics = Field(default_factory=ChannelMetrics)
    health_check_interval: int = Field(default=30, description="Seconds between health checks")
    last_health_check: datetime | None = Field(default=None)

    # Config
    config: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True

    def is_available(self) -> bool:
        """Check if channel is available for sending."""
        return self.enabled and self.status in (ChannelStatus.UP, ChannelStatus.DEGRADED)

    def score(self, priority: Priority = Priority.NORMAL) -> float:
        """
        Calculate channel score for routing.

        Lower score = better choice.
        """
        if not self.is_available():
            return float("inf")

        # Base score from latency
        score = self.metrics.latency_ms

        # Adjust for status
        if self.status == ChannelStatus.DEGRADED:
            score *= 2

        # Adjust for priority preferences
        match priority:
            case Priority.CRITICAL | Priority.HIGH:
                # Prefer low latency
                pass
            case Priority.LOW | Priority.BULK:
                # Prefer low cost
                score = self.cost_per_kb * 1000 + self.metrics.latency_ms * 0.1
            case _:
                # Balance latency and cost
                score = self.metrics.latency_ms + self.cost_per_kb * 100

        # Penalize for packet loss
        score += self.metrics.packet_loss * 10

        return score


class Command(BaseModel):
    """Command to be sent to a device."""

    id: str = Field(default_factory=generate_id)
    device_id: str = Field(..., description="Target device")
    cmd: str = Field(..., description="Command name")
    params: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Field(default=Priority.HIGH)
    timeout: int = Field(default=30, description="Timeout in seconds")
    created_at: datetime = Field(default_factory=datetime.now)


class CommandResult(BaseModel):
    """Result of a command execution."""

    command_id: str = Field(..., description="Original command ID")
    device_id: str = Field(...)
    success: bool = Field(...)
    pending: bool = Field(default=False, description="Command sent but no response yet")
    error: str | None = Field(default=None)
    data: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int | None = Field(default=None)
    received_at: datetime = Field(default_factory=datetime.now)


class RoutingResult(BaseModel):
    """Result of routing a message."""

    message_id: str = Field(...)
    success: bool = Field(...)
    channel: ChannelType | None = Field(default=None, description="Channel used")
    channels_tried: list[ChannelType] = Field(default_factory=list)
    queued: bool = Field(default=False, description="Message was queued for later")
    error: str | None = Field(default=None)
    duration_ms: float = Field(default=0)


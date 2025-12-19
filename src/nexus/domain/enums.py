"""Enumerations for MoMo-Nexus domain."""

from enum import Enum


class Priority(str, Enum):
    """Message priority levels."""

    CRITICAL = "critical"  # Immediate delivery, fastest channel
    HIGH = "high"  # Fast delivery, prefer low latency
    NORMAL = "normal"  # Standard delivery, best available
    LOW = "low"  # When convenient, prefer cheap (LoRa)
    BULK = "bulk"  # Large data transfer, prefer high bandwidth


class MessageType(str, Enum):
    """Types of messages in the system."""

    # Device → Nexus
    HELLO = "hello"  # Registration
    STATUS = "status"  # Heartbeat/status update
    ALERT = "alert"  # Alert/notification
    DATA = "data"  # Data payload
    RESULT = "result"  # Command result

    # Nexus → Device
    WELCOME = "welcome"  # Registration confirmed
    COMMAND = "command"  # Command to execute
    CONFIG = "config"  # Configuration update

    # Both directions
    ACK = "ack"  # Acknowledgment
    NACK = "nack"  # Negative acknowledgment
    PING = "ping"  # Keepalive
    PONG = "pong"  # Keepalive response
    ERROR = "error"  # Error message


class DeviceType(str, Enum):
    """Types of devices in the MoMo ecosystem."""

    MOMO = "momo"  # Main attack platform
    GHOSTBRIDGE = "ghostbridge"  # Network implant
    MIMIC = "mimic"  # USB attack device
    SWARM = "swarm"  # LoRa mesh node
    NEXUS = "nexus"  # This hub (self)
    UNKNOWN = "unknown"  # Unknown device type


class DeviceStatus(str, Enum):
    """Device status states."""

    UNREGISTERED = "unregistered"  # Not yet registered
    ONLINE = "online"  # Active and responding
    SLEEPING = "sleeping"  # Low power, periodic check-in
    OFFLINE = "offline"  # Not reachable
    LOST = "lost"  # No contact for extended period (24h+)


class ChannelType(str, Enum):
    """Types of communication channels."""

    LORA = "lora"  # LoRa mesh (Meshtastic)
    CELLULAR = "cellular"  # 4G/LTE modem
    WIFI = "wifi"  # WiFi client/AP
    BLE = "ble"  # Bluetooth Low Energy
    SATELLITE = "satellite"  # Satellite (Iridium)
    MOCK = "mock"  # Mock channel for testing


class ChannelStatus(str, Enum):
    """Channel health status."""

    UP = "up"  # Working normally
    DEGRADED = "degraded"  # Working but slow/unreliable
    DOWN = "down"  # Not working
    UNKNOWN = "unknown"  # Status not determined


class RoutingStrategy(str, Enum):
    """Routing strategies."""

    FASTEST = "fastest"  # Lowest latency
    CHEAPEST = "cheapest"  # Lowest data cost (LoRa preferred)
    RELIABLE = "reliable"  # Most reliable (multiple channels)
    AUTO = "auto"  # Automatic based on priority


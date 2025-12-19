"""
MoMo-Nexus Configuration System.

Pydantic-based configuration with YAML support.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from nexus.domain.enums import ChannelType, Priority

# =============================================================================
# Channel Configurations
# =============================================================================


class LoRaConfig(BaseModel):
    """LoRa channel configuration."""

    enabled: bool = True
    serial_port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200
    channel_name: str = "MoMo-Ops"
    psk: str | None = None  # Pre-shared key (auto-generated if None)
    region: str = "EU_868"  # EU_868, US_915, etc.
    tx_power: int = 20  # dBm


class CellularConfig(BaseModel):
    """4G/LTE cellular configuration."""

    enabled: bool = False
    serial_port: str = "/dev/ttyUSB1"
    baud_rate: int = 115200
    apn: str = "internet"
    pin: str | None = None
    api_endpoint: str | None = None  # HTTPS endpoint for cloud relay


class WiFiConfig(BaseModel):
    """WiFi channel configuration."""

    enabled: bool = True
    mode: str = "client"  # client, ap, both
    ssid: str | None = None
    password: str | None = None
    ap_ssid: str = "Nexus-AP"
    ap_password: str | None = None
    interface: str = "wlan0"


class BLEConfig(BaseModel):
    """BLE channel configuration."""

    enabled: bool = False
    adapter: str = "hci0"
    service_uuid: str = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART


class ChannelsConfig(BaseModel):
    """All channel configurations."""

    lora: LoRaConfig = Field(default_factory=LoRaConfig)
    cellular: CellularConfig = Field(default_factory=CellularConfig)
    wifi: WiFiConfig = Field(default_factory=WiFiConfig)
    ble: BLEConfig = Field(default_factory=BLEConfig)


# =============================================================================
# Routing Configuration
# =============================================================================


class RoutingConfig(BaseModel):
    """Message routing configuration."""

    # Priority → Channel mapping
    priority_channels: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "critical": ["cellular", "wifi", "lora"],
            "high": ["cellular", "wifi", "lora"],
            "normal": ["wifi", "lora", "cellular"],
            "low": ["lora", "wifi"],
            "bulk": ["wifi", "cellular"],
        }
    )

    # Retry settings
    max_retries: int = 5
    retry_backoff_base: float = 1.0  # seconds
    retry_backoff_max: float = 60.0  # seconds

    # ACK settings
    ack_timeout: int = 30  # seconds
    require_ack_for_commands: bool = True

    # Queue settings
    queue_max_size: int = 1000
    queue_persist: bool = True  # Persist queue to disk


# =============================================================================
# Fleet Configuration
# =============================================================================


class FleetConfig(BaseModel):
    """Fleet management configuration."""

    # Device registration
    auto_register: bool = True  # Auto-register unknown devices
    whitelist: list[str] = Field(default_factory=list)  # Empty = allow all
    blacklist: list[str] = Field(default_factory=list)

    # Health monitoring
    heartbeat_interval: int = 300  # seconds (5 min)
    heartbeat_timeout: int = 900  # seconds (15 min) → mark offline
    lost_timeout: int = 86400  # seconds (24h) → mark lost

    # Command dispatch
    command_timeout: int = 30  # seconds


# =============================================================================
# Server Configuration
# =============================================================================


class ServerConfig(BaseModel):
    """Server/API configuration."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8080

    # Authentication
    auth_enabled: bool = True
    api_key: str | None = None  # Auto-generated if None

    # WebSocket
    websocket_enabled: bool = True
    websocket_path: str = "/ws"

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


# =============================================================================
# Database Configuration
# =============================================================================


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: str = "data/nexus.db"
    message_retention_days: int = 30
    prune_on_startup: bool = True


# =============================================================================
# Logging Configuration
# =============================================================================


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"  # json, text
    file: str | None = "logs/nexus.log"
    rotation: str = "1 day"
    retention: str = "7 days"


# =============================================================================
# Security Configuration
# =============================================================================


class SecurityConfig(BaseModel):
    """Security configuration."""

    # Master key (hex-encoded, 64 chars = 32 bytes)
    master_key: str | None = None  # Auto-generated if None

    # Default security level: none, signed, encrypted
    default_level: str = "signed"

    # Replay protection
    replay_window: int = 300  # seconds
    max_nonces: int = 100000

    # Key rotation
    auto_rotate_keys: bool = False
    key_rotation_days: int = 30


# =============================================================================
# Geo Configuration
# =============================================================================


class GeoConfig(BaseModel):
    """GPS and geofencing configuration."""

    # Location tracking
    max_history: int = 1000  # Max points per device
    min_distance: float = 5.0  # Minimum movement in meters
    max_accuracy: float = 100.0  # Maximum acceptable accuracy

    # Geofencing
    default_alert_on_enter: bool = True
    default_alert_on_exit: bool = True


# =============================================================================
# Main Configuration
# =============================================================================


class NexusConfig(BaseSettings):
    """
    Main Nexus configuration.

    Loads from:
    1. Environment variables (NEXUS_*)
    2. Config file (nexus.yml)
    3. Default values
    """

    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Instance info
    device_id: str = "nexus-001"
    name: str = "Nexus Hub"
    version: str = "0.2.0"

    # Sub-configurations
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    fleet: FleetConfig = Field(default_factory=FleetConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    geo: GeoConfig = Field(default_factory=GeoConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> NexusConfig:
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)

    def get_enabled_channels(self) -> list[ChannelType]:
        """Get list of enabled channel types."""
        enabled = []
        if self.channels.lora.enabled:
            enabled.append(ChannelType.LORA)
        if self.channels.cellular.enabled:
            enabled.append(ChannelType.CELLULAR)
        if self.channels.wifi.enabled:
            enabled.append(ChannelType.WIFI)
        if self.channels.ble.enabled:
            enabled.append(ChannelType.BLE)
        return enabled

    def get_channels_for_priority(self, priority: Priority) -> list[ChannelType]:
        """Get ordered channel list for a priority level."""
        channel_names = self.routing.priority_channels.get(priority.value, ["lora"])
        return [ChannelType(name) for name in channel_names if name in ChannelType.__members__.values()]


# =============================================================================
# Config Loading Utility
# =============================================================================


_config: NexusConfig | None = None


def load_config(path: str | Path | None = None) -> NexusConfig:
    """
    Load and cache configuration.

    Args:
        path: Path to config file. If None, searches default locations.

    Returns:
        NexusConfig instance
    """
    global _config

    if _config is not None and path is None:
        return _config

    # Search order
    search_paths = [
        Path(path) if path else None,
        Path("nexus.yml"),
        Path("configs/nexus.yml"),
        Path("/etc/nexus/nexus.yml"),
        Path.home() / ".config/nexus/nexus.yml",
    ]

    for config_path in search_paths:
        if config_path and config_path.exists():
            _config = NexusConfig.from_yaml(config_path)
            return _config

    # No config file found, use defaults
    _config = NexusConfig()
    return _config


def get_config() -> NexusConfig:
    """Get cached configuration or load defaults."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


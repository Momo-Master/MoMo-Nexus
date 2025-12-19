"""Communication channels for MoMo-Nexus."""

from nexus.channels.base import BaseChannel, ChannelError
from nexus.channels.ble import BLEChannel
from nexus.channels.cellular import CellularChannel
from nexus.channels.lora import LoRaChannel
from nexus.channels.manager import ChannelManager
from nexus.channels.mock import LoopbackChannel, MockChannel, UnreliableChannel
from nexus.channels.wifi import WiFiChannel

__all__ = [
    # Base
    "BaseChannel",
    "ChannelError",
    # Mock (testing)
    "MockChannel",
    "LoopbackChannel",
    "UnreliableChannel",
    # Real channels
    "LoRaChannel",
    "CellularChannel",
    "WiFiChannel",
    "BLEChannel",
    # Manager
    "ChannelManager",
]

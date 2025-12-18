"""Communication channels for MoMo-Nexus."""

from nexus.channels.base import BaseChannel, ChannelError
from nexus.channels.mock import MockChannel, LoopbackChannel, UnreliableChannel
from nexus.channels.lora import LoRaChannel
from nexus.channels.cellular import CellularChannel
from nexus.channels.wifi import WiFiChannel
from nexus.channels.ble import BLEChannel
from nexus.channels.manager import ChannelManager

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

"""
MoMo-Swarm Protocol Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Message formats and protocol handling for LoRa mesh communication.
Integrated from MoMo-Swarm into Nexus.
"""

from __future__ import annotations

import json
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class SwarmMessageType(str, Enum):
    """Swarm message type codes."""
    ALERT = "alert"      # Device → Operator: Event notification
    STATUS = "status"    # Device → Operator: Periodic heartbeat
    CMD = "cmd"          # Operator → Device: Command execution
    ACK = "ack"          # Any → Any: Acknowledgment
    GPS = "gps"          # Device → Operator: Location update
    DATA = "data"        # Device → Operator: Data exfiltration


class EventCode(str, Enum):
    """Alert event codes from field devices."""
    # WiFi Events
    HANDSHAKE_CAPTURED = "hs_cap"
    PMKID_CAPTURED = "pmkid"
    NEW_AP = "new_ap"
    NEW_CLIENT = "new_cl"
    PASSWORD_CRACKED = "cracked"
    
    # Attack Events
    EVIL_TWIN_CONNECT = "et_conn"
    EVIL_TWIN_CREDENTIAL = "et_cred"
    KARMA_CLIENT = "karma"
    EAP_CREDENTIAL = "eap"
    WPA3_EVENT = "wpa3"
    
    # BLE Events
    BLE_DEVICE = "ble_dev"
    BLE_CONNECT = "ble_conn"
    
    # GhostBridge Events
    GHOST_BEACON = "gh_beacon"
    GHOST_TUNNEL = "gh_tunnel"
    GHOST_EXFIL = "gh_exfil"
    
    # Mimic Events
    MIMIC_TRIGGER = "mm_trig"
    MIMIC_INJECT = "mm_inject"
    
    # System Events
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    LOW_BATTERY = "low_bat"
    ALERT = "alert"


class CommandCode(str, Enum):
    """Command codes sent to field devices."""
    # General
    STATUS = "status"
    PING = "ping"
    MODE = "mode"
    SHELL = "shell"
    POWER = "power"
    CONFIG = "config"
    
    # MoMo Commands
    DEAUTH = "deauth"
    EVIL_TWIN = "eviltwin"
    KARMA = "karma"
    CAPTURE = "capture"
    CRACK = "crack"
    SCAN = "scan"
    
    # GhostBridge Commands
    GHOST_START = "gh_start"
    GHOST_STOP = "gh_stop"
    GHOST_TUNNEL = "gh_tunnel"
    
    # Mimic Commands
    MIMIC_ARM = "mm_arm"
    MIMIC_DISARM = "mm_disarm"
    MIMIC_TRIGGER = "mm_trigger"


class AckStatus(str, Enum):
    """Acknowledgment status codes."""
    OK = "ok"
    ERROR = "error"
    BUSY = "busy"
    QUEUED = "queued"
    TIMEOUT = "timeout"


# Maximum message size for Meshtastic/LoRa
MAX_SWARM_MESSAGE_SIZE = 237


@dataclass
class SwarmMessage:
    """
    MoMo-Swarm message format.
    
    All messages follow this JSON structure for LoRa transmission.
    Designed for minimal size while maintaining protocol clarity.
    """
    
    type: SwarmMessageType
    source: str
    data: dict[str, Any]
    version: int = 1
    destination: str | None = None
    timestamp: int = field(default_factory=lambda: int(time.time()))
    sequence: int = 0
    
    def to_json(self, compact: bool = True) -> str:
        """
        Serialize message to JSON string.
        
        Args:
            compact: Use compact JSON format (recommended for LoRa)
            
        Returns:
            JSON string representation
        """
        msg: dict[str, Any] = {
            "v": self.version,
            "t": self.type.value if isinstance(self.type, SwarmMessageType) else self.type,
            "src": self.source,
            "ts": self.timestamp,
            "seq": self.sequence,
            "d": self.data
        }
        
        if self.destination:
            msg["dst"] = self.destination
        
        if compact:
            return json.dumps(msg, separators=(',', ':'))
        return json.dumps(msg)
    
    def to_bytes(self) -> bytes:
        """Serialize message to bytes for transmission."""
        return self.to_json(compact=True).encode('utf-8')
    
    @classmethod
    def from_json(cls, json_str: str) -> SwarmMessage | None:
        """
        Parse message from JSON string.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            SwarmMessage object or None if parsing fails
        """
        try:
            data = json.loads(json_str)
            
            # Validate required fields
            required = ['v', 't', 'src', 'ts', 'seq', 'd']
            if not all(k in data for k in required):
                return None
            
            # Validate version
            if data['v'] != 1:
                return None
            
            # Parse message type
            try:
                msg_type = SwarmMessageType(data['t'])
            except ValueError:
                msg_type = data['t']  # type: ignore
            
            return cls(
                version=data['v'],
                type=msg_type,
                source=data['src'],
                destination=data.get('dst'),
                timestamp=data['ts'],
                sequence=data['seq'],
                data=data['d']
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    @classmethod
    def from_bytes(cls, data: bytes) -> SwarmMessage | None:
        """Parse message from bytes."""
        try:
            return cls.from_json(data.decode('utf-8'))
        except UnicodeDecodeError:
            return None
    
    def size(self) -> int:
        """Get serialized message size in bytes."""
        return len(self.to_bytes())
    
    def is_valid_size(self) -> bool:
        """Check if message fits within LoRa size limit."""
        return self.size() <= MAX_SWARM_MESSAGE_SIZE


class SwarmMessageBuilder:
    """
    Builder class for constructing MoMo-Swarm messages.
    
    Provides convenient methods for creating different message types
    with proper formatting and size management.
    """
    
    def __init__(self, device_id: str):
        """
        Initialize message builder.
        
        Args:
            device_id: This device's identifier (e.g., "momo-001", "nexus-hub")
        """
        self.device_id = device_id
        self._sequence = 0
    
    def _next_seq(self) -> int:
        """Get next sequence number (wraps at 65535)."""
        self._sequence = (self._sequence + 1) % 65536
        return self._sequence
    
    def alert(
        self,
        event: EventCode | str,
        data: dict[str, Any],
        destination: str | None = None
    ) -> SwarmMessage:
        """
        Create an alert message.
        
        Args:
            event: Event code (e.g., EventCode.HANDSHAKE_CAPTURED)
            data: Event-specific data
            destination: Optional destination device ID
            
        Returns:
            Alert message
        """
        return SwarmMessage(
            type=SwarmMessageType.ALERT,
            source=self.device_id,
            destination=destination,
            sequence=self._next_seq(),
            data={
                "evt": event.value if isinstance(event, EventCode) else event,
                **data
            }
        )
    
    def status(
        self,
        uptime: int,
        battery: int,
        temperature: int,
        gps: tuple[float, float],
        aps_seen: int = 0,
        handshakes: int = 0,
        detail: bool = False,
        **extra: Any
    ) -> SwarmMessage:
        """
        Create a status/heartbeat message.
        
        Args:
            uptime: Uptime in seconds
            battery: Battery percentage (0-100)
            temperature: CPU temperature in Celsius
            gps: (latitude, longitude) tuple
            aps_seen: Number of APs seen
            handshakes: Number of handshakes captured
            detail: Include detailed info
            **extra: Additional status fields
            
        Returns:
            Status message
        """
        data: dict[str, Any] = {
            "up": uptime,
            "bat": battery,
            "temp": temperature,
            "gps": list(gps),
            "aps": aps_seen,
            "hs": handshakes
        }
        
        if detail:
            data["detail"] = True
        
        data.update(extra)
        
        return SwarmMessage(
            type=SwarmMessageType.STATUS,
            source=self.device_id,
            sequence=self._next_seq(),
            data=data
        )
    
    def command(
        self,
        cmd: CommandCode | str,
        params: dict[str, Any],
        destination: str
    ) -> SwarmMessage:
        """
        Create a command message.
        
        Args:
            cmd: Command code
            params: Command parameters
            destination: Target device ID
            
        Returns:
            Command message
        """
        return SwarmMessage(
            type=SwarmMessageType.CMD,
            source=self.device_id,
            destination=destination,
            sequence=self._next_seq(),
            data={
                "cmd": cmd.value if isinstance(cmd, CommandCode) else cmd,
                **params
            }
        )
    
    def ack(
        self,
        ref_seq: int,
        status: AckStatus,
        destination: str,
        result: str | None = None,
        error: str | None = None
    ) -> SwarmMessage:
        """
        Create an acknowledgment message.
        
        Args:
            ref_seq: Sequence number of the message being acknowledged
            status: Ack status
            destination: Original sender's device ID
            result: Optional result data
            error: Optional error message
            
        Returns:
            Ack message
        """
        data: dict[str, Any] = {
            "ref": ref_seq,
            "status": status.value
        }
        
        if result:
            data["result"] = result[:200]  # Limit result size
        if error:
            data["error"] = error[:100]  # Limit error size
        
        return SwarmMessage(
            type=SwarmMessageType.ACK,
            source=self.device_id,
            destination=destination,
            sequence=self._next_seq(),
            data=data
        )
    
    def gps(
        self,
        lat: float,
        lon: float,
        alt: float = 0,
        speed: float = 0,
        hdop: float = 0,
        sats: int = 0
    ) -> SwarmMessage:
        """
        Create a GPS location message.
        
        Args:
            lat: Latitude
            lon: Longitude
            alt: Altitude in meters
            speed: Speed in m/s
            hdop: Horizontal dilution of precision
            sats: Number of satellites
            
        Returns:
            GPS message
        """
        return SwarmMessage(
            type=SwarmMessageType.GPS,
            source=self.device_id,
            sequence=self._next_seq(),
            data={
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "alt": int(alt),
                "speed": round(speed, 1),
                "hdop": round(hdop, 1),
                "sats": sats
            }
        )
    
    def data_chunk(
        self,
        chunk_id: str,
        name: str,
        chunk_num: int,
        total_chunks: int,
        data: str,
        destination: str
    ) -> SwarmMessage:
        """
        Create a data exfiltration chunk message.
        
        Args:
            chunk_id: Unique transfer ID
            name: File/data name
            chunk_num: Current chunk number (1-based)
            total_chunks: Total number of chunks
            data: Base64 encoded chunk data
            destination: Destination device ID
            
        Returns:
            Data message
        """
        return SwarmMessage(
            type=SwarmMessageType.DATA,
            source=self.device_id,
            destination=destination,
            sequence=self._next_seq(),
            data={
                "id": chunk_id,
                "name": name[:32],  # Limit filename
                "chunk": chunk_num,
                "total": total_chunks,
                "data": data
            }
        )


class SequenceTracker:
    """
    Track message sequence numbers to prevent replay attacks.
    
    Uses a sliding window approach to efficiently detect
    replay attempts while allowing for out-of-order delivery.
    """
    
    def __init__(self, window_size: int = 100):
        """
        Initialize sequence tracker.
        
        Args:
            window_size: Size of sequence window for replay detection
        """
        self.window_size = window_size
        self._last_seq: dict[str, int] = {}
        self._seen: dict[str, list[int]] = {}
    
    def is_valid(self, source: str, sequence: int) -> bool:
        """
        Check if sequence number is valid (not a replay).
        
        Args:
            source: Source device ID
            sequence: Sequence number to check
            
        Returns:
            True if valid, False if replay detected
        """
        last = self._last_seq.get(source, -1)
        
        # Handle wrap-around (65535 → 0)
        if sequence > last or (last > 60000 and sequence < 5000):
            self._last_seq[source] = sequence
            
            # Track recent sequences
            if source not in self._seen:
                self._seen[source] = []
            self._seen[source].append(sequence)
            
            # Trim old sequences
            if len(self._seen[source]) > self.window_size:
                self._seen[source] = self._seen[source][-self.window_size:]
            
            return True
        
        # Check if we've seen this exact sequence recently
        if source in self._seen and sequence in self._seen[source]:
            return False
        
        return False
    
    def reset(self, source: str | None = None) -> None:
        """
        Reset sequence tracking.
        
        Args:
            source: Specific source to reset, or None for all
        """
        if source:
            self._last_seq.pop(source, None)
            self._seen.pop(source, None)
        else:
            self._last_seq.clear()
            self._seen.clear()
    
    def get_stats(self) -> dict[str, Any]:
        """Get tracking statistics."""
        return {
            "tracked_sources": len(self._last_seq),
            "sources": list(self._last_seq.keys()),
            "total_sequences": sum(len(v) for v in self._seen.values()),
        }


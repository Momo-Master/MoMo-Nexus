"""
Cellular Channel (4G/LTE).

Provides high-bandwidth, long-range communication using 4G/LTE modems.
Supports SIM7600, Quectel, and other AT command based modems.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from nexus.channels.base import BaseChannel, ChannelError, ConnectionError, SendError
from nexus.domain.enums import ChannelType
from nexus.domain.models import Message

logger = logging.getLogger(__name__)

# Serial import (optional)
try:
    import serial
    import serial.tools.list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    serial = None  # type: ignore


class ModemState(str, Enum):
    """Modem state."""

    DISCONNECTED = "disconnected"
    INITIALIZING = "initializing"
    REGISTERED = "registered"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class SignalQuality:
    """Cellular signal quality."""

    rssi: int  # dBm
    ber: int  # Bit error rate
    rsrp: int | None = None  # LTE reference signal
    rsrq: int | None = None  # LTE quality
    sinr: int | None = None  # Signal to noise


@dataclass
class NetworkInfo:
    """Network registration info."""

    operator: str
    network_type: str  # 2G, 3G, 4G
    lac: str  # Location area code
    cell_id: str


class CellularChannel(BaseChannel):
    """
    Cellular channel using AT command modems.

    Supports:
    - SIM7600 series
    - Quectel EC25/EG25
    - Other AT command modems

    Communication modes:
    - HTTP/HTTPS requests
    - TCP socket connection
    - MQTT (via modem)

    Configuration:
        serial_port: Serial port (e.g., /dev/ttyUSB2, COM5)
        baud_rate: Baud rate (default 115200)
        apn: APN for data connection
        api_endpoint: HTTPS endpoint for message relay
        pin: SIM PIN if required
    """

    DEFAULT_BAUD_RATE = 115200
    AT_TIMEOUT = 5.0
    HTTP_TIMEOUT = 30.0

    def __init__(
        self,
        serial_port: str | None = None,
        baud_rate: int = DEFAULT_BAUD_RATE,
        apn: str = "internet",
        api_endpoint: str | None = None,
        pin: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            channel_type=ChannelType.CELLULAR,
            name="cellular",
            config=config or {},
        )

        if not SERIAL_AVAILABLE:
            logger.warning("pyserial not installed. Install with: pip install pyserial")

        self._serial_port = serial_port
        self._baud_rate = baud_rate
        self._apn = apn
        self._api_endpoint = api_endpoint
        self._pin = pin

        self._serial: Any = None
        self._modem_state = ModemState.DISCONNECTED
        self._signal: SignalQuality | None = None
        self._network: NetworkInfo | None = None
        self._imei: str | None = None
        self._iccid: str | None = None

        # Cellular is fast
        self._metrics.latency_ms = 100.0
        self._metrics.bandwidth_kbps = 1000.0  # ~1 Mbps typical

        # Track data usage
        self._data_sent = 0
        self._data_received = 0

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def modem_state(self) -> ModemState:
        """Get current modem state."""
        return self._modem_state

    @property
    def signal_quality(self) -> SignalQuality | None:
        """Get current signal quality."""
        return self._signal

    @property
    def network_info(self) -> NetworkInfo | None:
        """Get network registration info."""
        return self._network

    @property
    def imei(self) -> str | None:
        """Get modem IMEI."""
        return self._imei

    @property
    def data_usage(self) -> tuple[int, int]:
        """Get data usage (sent, received) in bytes."""
        return (self._data_sent, self._data_received)

    # =========================================================================
    # AT Commands
    # =========================================================================

    async def _send_at(
        self,
        command: str,
        timeout: float = AT_TIMEOUT,
        expect_ok: bool = True,
    ) -> list[str]:
        """
        Send AT command and get response.

        Args:
            command: AT command (without AT prefix)
            timeout: Response timeout
            expect_ok: Whether to expect OK response

        Returns:
            List of response lines
        """
        if not self._serial:
            raise ChannelError("Serial not connected")

        loop = asyncio.get_event_loop()

        def send_and_receive():
            # Clear input buffer
            self._serial.reset_input_buffer()

            # Send command
            cmd = f"AT{command}\r\n"
            self._serial.write(cmd.encode())

            # Read response
            lines = []
            start = asyncio.get_event_loop().time()

            while (asyncio.get_event_loop().time() - start) < timeout:
                if self._serial.in_waiting:
                    line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        lines.append(line)
                        if line in ("OK", "ERROR") or line.startswith("+CME ERROR"):
                            break

            return lines

        response = await loop.run_in_executor(None, send_and_receive)

        if expect_ok and "OK" not in response and any("ERROR" in line for line in response):
            raise ChannelError(f"AT command failed: {response}")

        return response

    async def _send_at_data(
        self,
        command: str,
        data: bytes,
        prompt: str = ">",
        timeout: float = HTTP_TIMEOUT,
    ) -> list[str]:
        """Send AT command with data payload."""
        if not self._serial:
            raise ChannelError("Serial not connected")

        loop = asyncio.get_event_loop()

        def send_with_data():
            self._serial.reset_input_buffer()

            # Send command
            cmd = f"AT{command}\r\n"
            self._serial.write(cmd.encode())

            # Wait for prompt
            start = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start) < 5:
                if self._serial.in_waiting:
                    response = self._serial.read(self._serial.in_waiting).decode(errors="ignore")
                    if prompt in response:
                        break

            # Send data
            self._serial.write(data)
            self._serial.write(b"\x1a")  # Ctrl+Z to end

            # Read response
            lines = []
            start = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start) < timeout:
                if self._serial.in_waiting:
                    line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        lines.append(line)
                        if "OK" in line or "ERROR" in line:
                            break

            return lines

        return await loop.run_in_executor(None, send_with_data)

    # =========================================================================
    # Connection
    # =========================================================================

    async def _connect(self) -> None:
        """Connect and initialize modem."""
        if not SERIAL_AVAILABLE:
            raise ConnectionError("pyserial not installed")

        self._modem_state = ModemState.INITIALIZING

        try:
            # Open serial port
            loop = asyncio.get_event_loop()

            port = self._serial_port or await self._find_modem_port()
            if not port:
                raise ConnectionError("No modem found")

            self._serial = await loop.run_in_executor(
                None,
                lambda: serial.Serial(
                    port,
                    self._baud_rate,
                    timeout=1,
                    write_timeout=1,
                ),
            )

            logger.info(f"Cellular modem opened on {port}")

            # Initialize modem
            await self._init_modem()

            # Check registration
            await self._check_network()

            # Setup data connection
            await self._setup_data()

            self._modem_state = ModemState.CONNECTED
            logger.info("Cellular channel connected and ready")

        except Exception as e:
            self._modem_state = ModemState.ERROR
            if self._serial:
                self._serial.close()
                self._serial = None
            raise ConnectionError(f"Modem initialization failed: {e}")

    async def _disconnect(self) -> None:
        """Disconnect modem."""
        try:
            if self._serial:
                # Deactivate PDP context
                with contextlib.suppress(Exception):
                    await self._send_at("+CIPSHUT", timeout=10, expect_ok=False)

                self._serial.close()
                self._serial = None

            self._modem_state = ModemState.DISCONNECTED
            logger.info("Cellular modem disconnected")

        except Exception as e:
            logger.warning(f"Error during cellular disconnect: {e}")

    async def _find_modem_port(self) -> str | None:
        """Auto-detect modem serial port."""
        if not SERIAL_AVAILABLE:
            return None

        loop = asyncio.get_event_loop()

        def find_port():
            ports = serial.tools.list_ports.comports()
            for port in ports:
                # Common modem VID/PID patterns
                if "1e0e" in str(port.vid) or "2c7c" in str(port.vid):  # SimCom, Quectel
                    return port.device
                if "modem" in port.description.lower():
                    return port.device
            return None

        return await loop.run_in_executor(None, find_port)

    async def _init_modem(self) -> None:
        """Initialize modem with basic commands."""
        # Reset
        await self._send_at("", expect_ok=False)  # Sync
        await self._send_at("E0")  # Echo off
        await self._send_at("+CMEE=2")  # Verbose errors

        # Get IMEI
        response = await self._send_at("+GSN")
        for line in response:
            if line.isdigit() and len(line) == 15:
                self._imei = line
                break

        # Get ICCID
        response = await self._send_at("+CCID", expect_ok=False)
        for line in response:
            if line.startswith("+CCID:"):
                self._iccid = line.split(":")[1].strip()
                break

        # Enter PIN if needed
        if self._pin:
            response = await self._send_at("+CPIN?")
            if any("SIM PIN" in line for line in response):
                await self._send_at(f'+CPIN="{self._pin}"')

        logger.info(f"Modem initialized, IMEI: {self._imei}")

    async def _check_network(self) -> None:
        """Check network registration."""
        # Check registration status
        for _ in range(30):  # Wait up to 30 seconds
            response = await self._send_at("+CREG?")
            for line in response:
                if "+CREG:" in line:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        status = int(parts[1].strip())
                        if status in (1, 5):  # Registered
                            self._modem_state = ModemState.REGISTERED
                            break

            if self._modem_state == ModemState.REGISTERED:
                break
            await asyncio.sleep(1)

        if self._modem_state != ModemState.REGISTERED:
            raise ConnectionError("Network registration failed")

        # Get operator info
        response = await self._send_at("+COPS?")
        for line in response:
            if "+COPS:" in line:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    operator = match.group(1)
                    self._network = NetworkInfo(
                        operator=operator,
                        network_type="4G",
                        lac="",
                        cell_id="",
                    )

        # Get signal quality
        await self._update_signal()

        logger.info(f"Registered on network: {self._network}")

    async def _setup_data(self) -> None:
        """Setup data connection."""
        # Set APN
        await self._send_at(f'+CGDCONT=1,"IP","{self._apn}"')

        # Activate PDP context
        try:
            await self._send_at("+CGACT=1,1", timeout=30)
        except Exception:
            # Some modems use different command
            await self._send_at("+CIICR", timeout=30, expect_ok=False)

        # Get IP address
        response = await self._send_at("+CGPADDR=1", expect_ok=False)
        logger.debug(f"Data connection established: {response}")

    async def _update_signal(self) -> None:
        """Update signal quality."""
        response = await self._send_at("+CSQ")
        for line in response:
            if "+CSQ:" in line:
                parts = line.split(":")[1].split(",")
                rssi_raw = int(parts[0].strip())
                ber = int(parts[1].strip()) if len(parts) > 1 else 99

                # Convert to dBm
                rssi = -999 if rssi_raw == 99 else -113 + rssi_raw * 2

                self._signal = SignalQuality(rssi=rssi, ber=ber)

    # =========================================================================
    # Sending
    # =========================================================================

    async def _send(self, message: Message) -> bool:
        """
        Send message via cellular.

        Uses HTTP POST to configured API endpoint.
        """
        if not self._api_endpoint:
            raise SendError("No API endpoint configured")

        if self._modem_state != ModemState.CONNECTED:
            raise SendError(f"Modem not connected: {self._modem_state}")

        try:
            # Serialize message
            import json

            payload = json.dumps(message.model_dump(mode="json"))
            payload_bytes = payload.encode("utf-8")

            # Track data usage
            self._data_sent += len(payload_bytes)

            # Send via HTTP POST
            success = await self._http_post(self._api_endpoint, payload_bytes)

            if success:
                logger.debug(f"Cellular sent message {message.id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Cellular send failed: {e}")
            raise SendError(f"Cellular send failed: {e}")

    async def _http_post(self, url: str, data: bytes) -> bool:
        """
        Send HTTP POST request via modem.

        Uses AT+HTTPACTION commands for SIM7600.
        """
        try:
            # Initialize HTTP
            await self._send_at("+HTTPINIT", expect_ok=False)
            await self._send_at("+HTTPPARA=\"CID\",1")
            await self._send_at(f'+HTTPPARA="URL","{url}"')
            await self._send_at('+HTTPPARA="CONTENT","application/json"')

            # Set data size
            await self._send_at(f"+HTTPDATA={len(data)},10000")

            # Wait for DOWNLOAD prompt and send data
            await asyncio.sleep(0.5)
            if self._serial:
                self._serial.write(data)

            await asyncio.sleep(1)

            # Execute POST
            response = await self._send_at("+HTTPACTION=1", timeout=30, expect_ok=False)

            # Check response
            success = False
            for line in response:
                if "+HTTPACTION:" in line:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        status = int(parts[1])
                        success = 200 <= status < 300

            # Terminate HTTP
            await self._send_at("+HTTPTERM", expect_ok=False)

            return success

        except Exception as e:
            logger.error(f"HTTP POST failed: {e}")
            # Try to clean up
            with contextlib.suppress(Exception):
                await self._send_at("+HTTPTERM", expect_ok=False)
            return False

    # =========================================================================
    # Health Check
    # =========================================================================

    async def _health_check(self) -> bool:
        """Check cellular channel health."""
        if not self._serial:
            return False

        try:
            # Simple AT check
            response = await self._send_at("", timeout=2)
            if "OK" not in response:
                return False

            # Update signal
            await self._update_signal()

            # Check signal strength
            if self._signal and self._signal.rssi < -110:
                logger.warning(f"Weak cellular signal: {self._signal.rssi} dBm")
                return False

            return True

        except Exception as e:
            logger.warning(f"Cellular health check failed: {e}")
            return False

    # =========================================================================
    # Utilities
    # =========================================================================

    async def send_sms(self, number: str, message: str) -> bool:
        """Send SMS message."""
        try:
            await self._send_at("+CMGF=1")  # Text mode
            await self._send_at(f'+CMGS="{number}"')

            # Send message with Ctrl+Z
            if self._serial:
                self._serial.write(message.encode())
                self._serial.write(b"\x1a")

            await asyncio.sleep(5)
            return True

        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return False

    async def get_location(self) -> tuple[float, float] | None:
        """Get location via cellular (LBS)."""
        try:
            response = await self._send_at("+CLBS=1,1", timeout=30)
            for line in response:
                if "+CLBS:" in line:
                    parts = line.split(",")
                    if len(parts) >= 3:
                        lat = float(parts[1])
                        lon = float(parts[2])
                        return (lat, lon)
        except Exception as e:
            logger.warning(f"Location query failed: {e}")

        return None


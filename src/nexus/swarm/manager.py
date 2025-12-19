"""
Swarm Manager
~~~~~~~~~~~~~

High-level manager for Swarm functionality in Nexus.
Integrates with Fleet, Channels, and API components.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nexus.swarm.bridge import SwarmBridge, SwarmConfig, BridgeStats
from nexus.swarm.protocol import (
    EventCode,
    CommandCode,
    SwarmMessage,
)

logger = logging.getLogger(__name__)


class SwarmManager:
    """
    High-level manager for Swarm mesh network functionality.
    
    Integrates:
    - LoRaChannel for physical transmission
    - SwarmBridge for protocol handling
    - Fleet registry for device tracking
    - Event system for notifications
    
    Example:
        >>> from nexus.channels import LoRaChannel, ChannelManager
        >>> from nexus.swarm import SwarmManager
        >>>
        >>> channel_mgr = ChannelManager()
        >>> await channel_mgr.add_channel(LoRaChannel(serial_port="/dev/ttyUSB0"))
        >>>
        >>> swarm = SwarmManager(channel_manager=channel_mgr)
        >>> await swarm.start()
        >>>
        >>> # Send command to field device
        >>> await swarm.send_command("momo-001", CommandCode.STATUS, {})
        >>>
        >>> # Broadcast alert
        >>> await swarm.broadcast_alert(EventCode.NEW_AP, {"ssid": "CorporateWiFi"})
    """
    
    def __init__(
        self,
        channel_manager: Any = None,
        fleet_registry: Any = None,
        config: SwarmConfig | None = None,
    ):
        """
        Initialize Swarm manager.
        
        Args:
            channel_manager: Nexus ChannelManager instance
            fleet_registry: Nexus Fleet Registry instance
            config: Swarm configuration
        """
        self._channel_mgr = channel_manager
        self._fleet = fleet_registry
        self.config = config or SwarmConfig()
        
        self._bridge: SwarmBridge | None = None
        self._lora_channel: Any = None
        self._running = False
        
        # Event handlers
        self._alert_handlers: list[Any] = []
    
    # ==================== Lifecycle ====================
    
    async def start(self) -> bool:
        """
        Start Swarm manager.
        
        Returns:
            True if started successfully
        """
        if not self.config.enabled:
            logger.warning("Swarm is disabled in config")
            return False
        
        # Get LoRa channel from manager
        if self._channel_mgr:
            from nexus.domain.enums import ChannelType
            self._lora_channel = self._channel_mgr.get_channel(ChannelType.LORA)
        
        if not self._lora_channel:
            logger.warning("No LoRa channel available, Swarm will be limited")
        
        # Create bridge
        self._bridge = SwarmBridge(
            lora_channel=self._lora_channel,
            config=self.config,
        )
        
        # Register event handler
        self._bridge.on_event(self._on_device_event)
        
        # Start bridge
        success = await self._bridge.start()
        
        if success:
            self._running = True
            logger.info("Swarm manager started")
        
        return success
    
    async def stop(self) -> None:
        """Stop Swarm manager."""
        if self._bridge:
            await self._bridge.stop()
        
        self._running = False
        logger.info("Swarm manager stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running
    
    # ==================== Commands ====================
    
    async def send_command(
        self,
        device_id: str,
        command: CommandCode | str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send command to a field device.
        
        Args:
            device_id: Target device ID
            command: Command to send
            params: Command parameters
            
        Returns:
            True if command was sent
        """
        if not self._bridge or not self._running:
            logger.error("Swarm not running")
            return False
        
        return self._bridge.send_command(command, params or {}, device_id)
    
    async def broadcast_command(
        self,
        command: CommandCode | str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Broadcast command to all devices.
        
        Args:
            command: Command to send
            params: Command parameters
            
        Returns:
            True if command was sent
        """
        if not self._bridge or not self._running:
            return False
        
        # Send without destination = broadcast
        if self._bridge:
            msg = self._bridge.builder.command(command, params or {}, "broadcast")
            await self._bridge._send_swarm_message(msg)
            return True
        
        return False
    
    # ==================== Alerts ====================
    
    async def send_alert(
        self,
        event: EventCode | str,
        data: dict[str, Any],
        destination: str | None = None,
    ) -> bool:
        """
        Send alert notification.
        
        Args:
            event: Event code
            data: Event data
            destination: Optional target device
            
        Returns:
            True if alert was sent
        """
        if not self._bridge or not self._running:
            return False
        
        return self._bridge.send_alert(event, data, destination)
    
    async def broadcast_alert(
        self,
        event: EventCode | str,
        data: dict[str, Any],
    ) -> bool:
        """
        Broadcast alert to all listeners.
        
        Args:
            event: Event code
            data: Event data
            
        Returns:
            True if alert was sent
        """
        return await self.send_alert(event, data, None)
    
    # ==================== Device Management ====================
    
    def get_devices(self) -> dict[str, dict[str, Any]]:
        """Get all known Swarm devices."""
        if self._bridge:
            return self._bridge.get_devices()
        return {}
    
    def get_device(self, device_id: str) -> dict[str, Any] | None:
        """Get info for a specific device."""
        if self._bridge:
            return self._bridge.get_device(device_id)
        return None
    
    async def ping_device(self, device_id: str) -> bool:
        """
        Ping a device to check if it's online.
        
        Args:
            device_id: Device to ping
            
        Returns:
            True if ping was sent (not necessarily received)
        """
        return await self.send_command(device_id, CommandCode.PING, {})
    
    async def request_status(self, device_id: str, detail: bool = False) -> bool:
        """
        Request status from a device.
        
        Args:
            device_id: Device to query
            detail: Include detailed info
            
        Returns:
            True if request was sent
        """
        return await self.send_command(device_id, CommandCode.STATUS, {"detail": detail})
    
    # ==================== Events ====================
    
    def on_alert(self, handler: Any) -> None:
        """
        Register handler for device alerts.
        
        Args:
            handler: Async function(event_code, data)
        """
        self._alert_handlers.append(handler)
    
    async def _on_device_event(self, event: str, data: dict[str, Any]) -> None:
        """Handle event from device."""
        # Update fleet registry if available
        if self._fleet and "src" in data:
            device_id = data.get("src")
            try:
                # Update last seen
                await self._fleet.update_device(device_id, {"last_event": event})
            except Exception:
                pass
        
        # Forward to alert handlers
        for handler in self._alert_handlers:
            try:
                await handler(event, data)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    # ==================== Statistics ====================
    
    def get_stats(self) -> BridgeStats | None:
        """Get bridge statistics."""
        if self._bridge:
            return self._bridge.stats
        return None
    
    # ==================== MoMo Integration ====================
    
    async def forward_momo_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> bool:
        """
        Forward event from MoMo to Swarm network.
        
        This is called by MoMo plugin to broadcast events.
        
        Args:
            event_type: Type of event
            data: Event data
            
        Returns:
            True if forwarded
        """
        # Map MoMo event types to Swarm EventCodes
        event_map = {
            'handshake_captured': EventCode.HANDSHAKE_CAPTURED,
            'pmkid_captured': EventCode.PMKID_CAPTURED,
            'new_ap': EventCode.NEW_AP,
            'new_ap_strong': EventCode.NEW_AP,
            'ble_device': EventCode.BLE_DEVICE,
            'crack_complete': EventCode.PASSWORD_CRACKED,
            'evil_twin_connect': EventCode.EVIL_TWIN_CONNECT,
            'credential_captured': EventCode.EVIL_TWIN_CREDENTIAL,
            'karma_client': EventCode.KARMA_CLIENT,
        }
        
        # Check if we should forward
        if event_type not in self.config.forward_events:
            return False
        
        event_code = event_map.get(event_type, event_type)
        return await self.broadcast_alert(event_code, data)
    
    # ==================== GhostBridge Integration ====================
    
    async def forward_ghost_beacon(self, data: dict[str, Any]) -> bool:
        """Forward GhostBridge beacon to Swarm."""
        return await self.broadcast_alert(EventCode.GHOST_BEACON, data)
    
    async def ghost_command(
        self,
        device_id: str,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send command to GhostBridge device.
        
        Args:
            device_id: GhostBridge device ID
            action: Action (start, stop, tunnel)
            params: Action parameters
            
        Returns:
            True if command sent
        """
        cmd_map = {
            "start": CommandCode.GHOST_START,
            "stop": CommandCode.GHOST_STOP,
            "tunnel": CommandCode.GHOST_TUNNEL,
        }
        
        cmd = cmd_map.get(action, action)
        return await self.send_command(device_id, cmd, params or {})
    
    # ==================== Mimic Integration ====================
    
    async def forward_mimic_trigger(self, data: dict[str, Any]) -> bool:
        """Forward Mimic trigger event to Swarm."""
        return await self.broadcast_alert(EventCode.MIMIC_TRIGGER, data)
    
    async def mimic_command(
        self,
        device_id: str,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send command to Mimic device.
        
        Args:
            device_id: Mimic device ID
            action: Action (arm, disarm, trigger)
            params: Action parameters
            
        Returns:
            True if command sent
        """
        cmd_map = {
            "arm": CommandCode.MIMIC_ARM,
            "disarm": CommandCode.MIMIC_DISARM,
            "trigger": CommandCode.MIMIC_TRIGGER,
        }
        
        cmd = cmd_map.get(action, action)
        return await self.send_command(device_id, cmd, params or {})
    
    # ==================== Context Manager ====================
    
    async def __aenter__(self) -> SwarmManager:
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()


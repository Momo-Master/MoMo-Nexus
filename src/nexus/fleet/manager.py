"""
Fleet Manager.

Central orchestration for all fleet management components.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nexus.config import NexusConfig, get_config
from nexus.core.events import EventBus, EventType, get_event_bus
from nexus.domain.enums import DeviceStatus, MessageType
from nexus.domain.models import Device, Message
from nexus.fleet.alerts import AlertManager, AlertSeverity, AlertType
from nexus.fleet.commands import CommandDispatcher
from nexus.fleet.monitor import HealthMonitor
from nexus.fleet.registry import DeviceRegistry
from nexus.infrastructure.database import DeviceStore

if TYPE_CHECKING:
    from nexus.core.router import Router

logger = logging.getLogger(__name__)


class FleetManager:
    """
    Central fleet management orchestrator.

    Integrates:
    - Device Registry
    - Health Monitor
    - Command Dispatcher
    - Alert Manager

    Handles incoming messages and coordinates responses.
    """

    def __init__(
        self,
        router: Router,
        config: NexusConfig | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._router = router
        self._config = config or get_config()
        self._event_bus = event_bus or get_event_bus()

        # Components
        self._registry = DeviceRegistry(
            config=self._config,
            event_bus=self._event_bus,
        )
        self._monitor = HealthMonitor(
            registry=self._registry,
            config=self._config,
            event_bus=self._event_bus,
        )
        self._commands = CommandDispatcher(
            router=self._router,
            registry=self._registry,
            config=self._config,
            event_bus=self._event_bus,
        )
        self._alerts = AlertManager(
            event_bus=self._event_bus,
        )

        # Database store
        self._store: DeviceStore | None = None

        # State
        self._running = False

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def registry(self) -> DeviceRegistry:
        """Get device registry."""
        return self._registry

    @property
    def monitor(self) -> HealthMonitor:
        """Get health monitor."""
        return self._monitor

    @property
    def commands(self) -> CommandDispatcher:
        """Get command dispatcher."""
        return self._commands

    @property
    def alerts(self) -> AlertManager:
        """Get alert manager."""
        return self._alerts

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self, store: DeviceStore | None = None) -> None:
        """
        Start fleet management.

        Args:
            store: Optional device store for persistence
        """
        if self._running:
            return

        self._store = store
        self._running = True

        # Initialize registry with database
        await self._registry.initialize(store)

        # Start health monitor
        await self._monitor.start()

        # Subscribe to events
        self._event_bus.subscribe(EventType.MESSAGE_RECEIVED, self._on_message_received)
        self._event_bus.subscribe(EventType.DEVICE_OFFLINE, self._on_device_offline)
        self._event_bus.subscribe(EventType.DEVICE_LOST, self._on_device_lost)

        logger.info("Fleet manager started")

    async def stop(self) -> None:
        """Stop fleet management."""
        self._running = False

        # Unsubscribe from events
        self._event_bus.unsubscribe(EventType.MESSAGE_RECEIVED, self._on_message_received)
        self._event_bus.unsubscribe(EventType.DEVICE_OFFLINE, self._on_device_offline)
        self._event_bus.unsubscribe(EventType.DEVICE_LOST, self._on_device_lost)

        # Stop monitor
        await self._monitor.stop()

        logger.info("Fleet manager stopped")

    # =========================================================================
    # Message Handling
    # =========================================================================

    async def _on_message_received(self, event: Any) -> None:
        """Handle incoming message event."""
        # This is called from event bus, extract message info
        data = event.data if hasattr(event, "data") else {}
        data.get("type")
        source = data.get("source")

        if not source:
            return

        # Record activity
        await self._monitor.record_message(source)

    async def handle_message(self, message: Message) -> None:
        """
        Handle incoming message from device.

        Routes to appropriate handler based on message type.
        """
        msg_type = message.type

        # Update last seen
        await self._monitor.record_message(message.src)

        # Route by type
        match msg_type:
            case MessageType.HELLO:
                await self._handle_hello(message)

            case MessageType.STATUS:
                await self._handle_status(message)

            case MessageType.ALERT:
                await self._handle_alert(message)

            case MessageType.RESULT:
                await self._handle_result(message)

            case MessageType.PING:
                await self._handle_ping(message)

            case _:
                logger.debug(f"Unhandled message type: {msg_type}")

    async def _handle_hello(self, message: Message) -> None:
        """Handle device registration."""
        device = await self._registry.register_from_hello(message)

        if device:
            # Send welcome response
            welcome = Message(
                src="nexus",
                dst=message.src,
                type=MessageType.WELCOME,
                data={
                    "status": "registered",
                    "device_id": device.id,
                    "heartbeat_interval": self._config.fleet.heartbeat_interval,
                },
            )
            await self._router.route(welcome)

            logger.info(f"Device registered and welcomed: {device.id}")
        else:
            # Send rejection
            reject = Message(
                src="nexus",
                dst=message.src,
                type=MessageType.ERROR,
                data={
                    "error": "registration_rejected",
                    "message": "Device not allowed to register",
                },
            )
            await self._router.route(reject)

    async def _handle_status(self, message: Message) -> None:
        """Handle status/heartbeat message."""
        await self._monitor.process_heartbeat(message.src, message.data)

        # Update device info
        await self._registry.update(
            message.src,
            status=DeviceStatus.ONLINE,
            battery=message.data.get("battery"),
            location=message.data.get("location"),
        )

    async def _handle_alert(self, message: Message) -> None:
        """Handle alert message."""
        alert = await self._alerts.create_from_message(message)
        logger.info(f"Alert from {message.src}: {alert.title}")

    async def _handle_result(self, message: Message) -> None:
        """Handle command result."""
        await self._commands.handle_result(message)

    async def _handle_ping(self, message: Message) -> None:
        """Handle ping message."""
        pong = Message(
            src="nexus",
            dst=message.src,
            type=MessageType.PONG,
            ack_id=message.id,
        )
        await self._router.route(pong)

    # =========================================================================
    # Event Handlers
    # =========================================================================

    async def _on_device_offline(self, event: Any) -> None:
        """Handle device offline event."""
        data = event.data if hasattr(event, "data") else {}
        device_id = data.get("device_id")

        if device_id:
            await self._alerts.create(
                type=AlertType.DEVICE_OFFLINE,
                severity=AlertSeverity.MEDIUM,
                title=f"Device offline: {device_id}",
                message=f"Device {device_id} has not responded for {data.get('seconds_ago', 0):.0f} seconds",
                device_id=device_id,
                data=data,
            )

    async def _on_device_lost(self, event: Any) -> None:
        """Handle device lost event."""
        data = event.data if hasattr(event, "data") else {}
        device_id = data.get("device_id")

        if device_id:
            await self._alerts.create(
                type=AlertType.DEVICE_LOST,
                severity=AlertSeverity.HIGH,
                title=f"Device lost: {device_id}",
                message=f"Device {device_id} has not been seen for over 24 hours",
                device_id=device_id,
                data=data,
            )

    # =========================================================================
    # Commands
    # =========================================================================

    async def send_command(
        self,
        device_id: str,
        cmd: str,
        params: dict[str, Any] | None = None,
        wait: bool = True,
        timeout: float | None = None,
    ) -> Any:
        """
        Send command to device.

        Args:
            device_id: Target device
            cmd: Command name
            params: Command parameters
            wait: Wait for result
            timeout: Command timeout

        Returns:
            CommandResult
        """
        return await self._commands.dispatch(
            device_id=device_id,
            cmd=cmd,
            params=params,
            wait=wait,
            timeout=timeout,
        )

    async def broadcast_command(
        self,
        cmd: str,
        params: dict[str, Any] | None = None,
        device_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Broadcast command to multiple devices.

        Args:
            cmd: Command name
            params: Command parameters
            device_type: Filter by device type

        Returns:
            Dict of device_id -> CommandResult
        """
        return await self._commands.dispatch_broadcast(
            cmd=cmd,
            params=params,
            device_type=device_type,
        )

    # =========================================================================
    # Queries
    # =========================================================================

    async def get_device(self, device_id: str) -> Device | None:
        """Get device by ID."""
        return await self._registry.get(device_id)

    async def get_all_devices(self) -> list[Device]:
        """Get all devices."""
        return await self._registry.get_all()

    async def get_online_devices(self) -> list[Device]:
        """Get online devices."""
        return await self._registry.get_online()

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get fleet statistics."""
        registry_stats = await self._registry.get_stats()
        health_stats = await self._monitor.get_stats()
        command_stats = await self._commands.get_stats()
        alert_stats = await self._alerts.get_stats()

        return {
            "registry": registry_stats,
            "health": health_stats,
            "commands": command_stats,
            "alerts": alert_stats,
            "running": self._running,
        }

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get data for dashboard display."""
        devices = await self._registry.get_all()
        recent_alerts = await self._alerts.get_recent(10)
        critical = await self._alerts.get_critical()

        return {
            "devices": [
                {
                    "id": d.id,
                    "type": d.type.value if hasattr(d.type, "value") else d.type,
                    "name": d.name,
                    "status": d.status.value if hasattr(d.status, "value") else d.status,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    "battery": d.battery,
                    "location": d.location.to_tuple() if d.location else None,
                }
                for d in devices
            ],
            "alerts": [
                {
                    "id": a.id,
                    "type": a.type.value,
                    "severity": a.severity.value,
                    "title": a.title,
                    "timestamp": a.timestamp.isoformat(),
                    "acknowledged": a.acknowledged,
                }
                for a in recent_alerts
            ],
            "critical_alerts": len(critical),
            "summary": await self._registry.get_stats(),
        }


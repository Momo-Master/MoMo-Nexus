"""
MoMo-Nexus Application.

Main application entrypoint and orchestration.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Any

from nexus._version import __version__
from nexus.channels.manager import ChannelManager
from nexus.config import NexusConfig, load_config
from nexus.core.events import EventType, get_event_bus
from nexus.core.router import Router
from nexus.fleet.manager import FleetManager
from nexus.geo.manager import GeoManager
from nexus.infrastructure.database import DeviceStore, MessageStore
from nexus.plugins.manager import PluginManager
from nexus.security.manager import SecurityManager

logger = logging.getLogger(__name__)


class NexusApp:
    """
    Main Nexus application.

    Orchestrates all components:
    - Channel Manager
    - Message Router
    - Fleet Manager
    - Security Manager
    - Geo Manager
    - Plugin Manager
    - API Server (optional)
    """

    def __init__(self, config: NexusConfig | None = None) -> None:
        self._config = config or load_config()
        self._event_bus = get_event_bus()

        # Components (initialized on start)
        self._router: Router | None = None
        self._channel_manager: ChannelManager | None = None
        self._fleet_manager: FleetManager | None = None
        self._security_manager: SecurityManager | None = None
        self._geo_manager: GeoManager | None = None
        self._plugin_manager: PluginManager | None = None

        # Stores
        self._device_store: DeviceStore | None = None
        self._message_store: MessageStore | None = None

        # State
        self._running = False
        self._started_at: datetime | None = None
        self._shutdown_event = asyncio.Event()

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def config(self) -> NexusConfig:
        """Get configuration."""
        return self._config

    @property
    def router(self) -> Router | None:
        """Get message router."""
        return self._router

    @property
    def channel_manager(self) -> ChannelManager | None:
        """Get channel manager."""
        return self._channel_manager

    @property
    def fleet_manager(self) -> FleetManager | None:
        """Get fleet manager."""
        return self._fleet_manager

    @property
    def is_running(self) -> bool:
        """Check if app is running."""
        return self._running

    @property
    def uptime(self) -> float:
        """Get uptime in seconds."""
        if self._started_at:
            return (datetime.now() - self._started_at).total_seconds()
        return 0

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> None:
        """Start the Nexus application."""
        if self._running:
            return

        logger.info(f"Starting MoMo-Nexus v{__version__}")
        logger.info(f"Device ID: {self._config.device_id}")

        try:
            # Initialize stores
            await self._init_stores()

            # Initialize components
            await self._init_components()

            # Start components
            await self._start_components()

            # Setup signal handlers
            self._setup_signals()

            self._running = True
            self._started_at = datetime.now()

            # Emit startup event
            await self._event_bus.emit(
                EventType.SYSTEM_STARTUP,
                {
                    "version": __version__,
                    "device_id": self._config.device_id,
                },
            )

            logger.info("MoMo-Nexus started successfully")

        except Exception as e:
            logger.error(f"Failed to start Nexus: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the Nexus application."""
        if not self._running:
            return

        logger.info("Stopping MoMo-Nexus...")

        # Emit shutdown event
        await self._event_bus.emit(EventType.SYSTEM_SHUTDOWN, {})

        # Stop components in reverse order
        await self._stop_components()

        # Close stores
        await self._close_stores()

        self._running = False
        self._shutdown_event.set()

        logger.info("MoMo-Nexus stopped")

    async def run_forever(self) -> None:
        """Run until shutdown signal."""
        await self.start()

        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()

    # =========================================================================
    # Initialization
    # =========================================================================

    async def _init_stores(self) -> None:
        """Initialize database stores."""
        db_path = self._config.database.path

        self._device_store = DeviceStore(db_path)
        self._message_store = MessageStore(db_path)

        await self._device_store.connect()
        await self._message_store.connect()

        logger.debug("Database stores initialized")

    async def _close_stores(self) -> None:
        """Close database stores."""
        if self._device_store:
            await self._device_store.disconnect()
        if self._message_store:
            await self._message_store.disconnect()

    async def _init_components(self) -> None:
        """Initialize all components."""
        # Router
        self._router = Router(
            config=self._config,
            event_bus=self._event_bus,
        )

        # Channel Manager
        self._channel_manager = ChannelManager(
            config=self._config,
            event_bus=self._event_bus,
        )

        # Fleet Manager
        self._fleet_manager = FleetManager(
            router=self._router,
            config=self._config,
            event_bus=self._event_bus,
        )

        # Security Manager
        self._security_manager = SecurityManager(
            config=self._config,
            event_bus=self._event_bus,
        )

        # Geo Manager
        self._geo_manager = GeoManager(
            config=self._config,
            event_bus=self._event_bus,
        )

        # Plugin Manager
        self._plugin_manager = PluginManager(
            config=self._config,
            event_bus=self._event_bus,
        )

        logger.debug("Components initialized")

    async def _start_components(self) -> None:
        """Start all components."""
        # Start channel manager and register channels
        await self._channel_manager.start()

        # Register channels with router
        for channel in self._channel_manager.get_all_channels():
            self._router.register_channel(channel)

        # Start router
        await self._router.start()

        # Start fleet manager
        await self._fleet_manager.start(store=self._device_store)

        # Start security manager
        await self._security_manager.start()

        # Start geo manager
        await self._geo_manager.start()

        # Start plugins
        await self._plugin_manager.start_all()

        logger.debug("Components started")

    async def _stop_components(self) -> None:
        """Stop all components."""
        if self._plugin_manager:
            await self._plugin_manager.stop_all()
            await self._plugin_manager.unload_all()

        if self._geo_manager:
            await self._geo_manager.stop()

        if self._security_manager:
            await self._security_manager.stop()

        if self._fleet_manager:
            await self._fleet_manager.stop()

        if self._router:
            await self._router.stop()

        if self._channel_manager:
            await self._channel_manager.stop()

    def _setup_signals(self) -> None:
        """Setup signal handlers."""
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self.request_shutdown)

    # =========================================================================
    # Status
    # =========================================================================

    async def get_status(self) -> dict[str, Any]:
        """Get application status."""
        return {
            "running": self._running,
            "version": __version__,
            "device_id": self._config.device_id,
            "uptime": self.uptime,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "channels": self._channel_manager.get_status() if self._channel_manager else {},
            "router": await self._router.get_stats() if self._router else {},
            "fleet": await self._fleet_manager.get_stats() if self._fleet_manager else {},
        }


# =============================================================================
# Convenience Functions
# =============================================================================


async def run_nexus(config: NexusConfig | None = None) -> None:
    """Run Nexus application."""
    app = NexusApp(config)
    await app.run_forever()


def main() -> None:
    """Main entry point."""
    from nexus.cli import app as cli_app
    cli_app()


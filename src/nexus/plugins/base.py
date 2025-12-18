"""
Plugin base classes.

Defines the interface for Nexus plugins.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nexus.config import NexusConfig
    from nexus.core.events import EventBus

logger = logging.getLogger(__name__)


class PluginState(str, Enum):
    """Plugin lifecycle states."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class PluginCapability(str, Enum):
    """Plugin capability flags."""

    # Message handling
    MESSAGE_HANDLER = "message_handler"
    MESSAGE_FILTER = "message_filter"
    MESSAGE_TRANSFORM = "message_transform"

    # Device handling
    DEVICE_HANDLER = "device_handler"
    DEVICE_AUTH = "device_auth"

    # Channel extensions
    CHANNEL_DRIVER = "channel_driver"

    # Alert handling
    ALERT_HANDLER = "alert_handler"
    ALERT_NOTIFIER = "alert_notifier"

    # Data processing
    DATA_PROCESSOR = "data_processor"
    DATA_STORAGE = "data_storage"

    # UI extensions
    WEB_ROUTE = "web_route"
    WEB_WIDGET = "web_widget"

    # System
    BACKGROUND_TASK = "background_task"
    SCHEDULED_TASK = "scheduled_task"


@dataclass
class PluginMetadata:
    """
    Plugin metadata.

    Attributes:
        id: Unique plugin identifier
        name: Human-readable name
        version: Plugin version string
        description: Short description
        author: Plugin author
        dependencies: Required plugin IDs
        capabilities: Plugin capabilities
        config_schema: Configuration schema (JSON Schema)
    """

    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    homepage: str = ""
    dependencies: list[str] = field(default_factory=list)
    capabilities: list[PluginCapability] = field(default_factory=list)
    config_schema: dict[str, Any] | None = None
    min_nexus_version: str = "0.1.0"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "dependencies": self.dependencies,
            "capabilities": [c.value for c in self.capabilities],
            "min_nexus_version": self.min_nexus_version,
        }


class Plugin(ABC):
    """
    Base class for all Nexus plugins.

    Plugins extend Nexus functionality through:
    - Hooks for message/event processing
    - Custom commands
    - Alert handlers
    - Background tasks
    """

    # Class-level metadata (override in subclass)
    metadata: PluginMetadata

    def __init__(self) -> None:
        self._state = PluginState.UNLOADED
        self._config: dict[str, Any] = {}
        self._nexus_config: "NexusConfig | None" = None
        self._event_bus: "EventBus | None" = None
        self._context: dict[str, Any] = {}
        self._loaded_at: datetime | None = None
        self._started_at: datetime | None = None
        self._error: str | None = None

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def state(self) -> PluginState:
        """Get current plugin state."""
        return self._state

    @property
    def config(self) -> dict[str, Any]:
        """Get plugin configuration."""
        return self._config

    @property
    def is_running(self) -> bool:
        """Check if plugin is running."""
        return self._state == PluginState.RUNNING

    @property
    def id(self) -> str:
        """Get plugin ID."""
        return self.metadata.id

    @property
    def name(self) -> str:
        """Get plugin name."""
        return self.metadata.name

    @property
    def version(self) -> str:
        """Get plugin version."""
        return self.metadata.version

    # =========================================================================
    # Lifecycle Methods (Override in subclass)
    # =========================================================================

    async def on_load(self) -> None:
        """
        Called when plugin is loaded.

        Use for initialization that doesn't require running services.
        """
        pass

    async def on_unload(self) -> None:
        """
        Called when plugin is unloaded.

        Use for cleanup.
        """
        pass

    async def on_start(self) -> None:
        """
        Called when plugin is started.

        Use for starting background tasks, subscribing to events.
        """
        pass

    async def on_stop(self) -> None:
        """
        Called when plugin is stopped.

        Use for graceful shutdown of tasks.
        """
        pass

    async def on_config_change(self, config: dict[str, Any]) -> None:
        """
        Called when plugin configuration changes.

        Args:
            config: New configuration
        """
        self._config = config

    # =========================================================================
    # Internal Lifecycle (Called by PluginManager)
    # =========================================================================

    async def _load(
        self,
        config: dict[str, Any],
        nexus_config: "NexusConfig",
        event_bus: "EventBus",
    ) -> None:
        """Internal load method."""
        self._state = PluginState.LOADING
        self._config = config
        self._nexus_config = nexus_config
        self._event_bus = event_bus

        try:
            await self.on_load()
            self._state = PluginState.LOADED
            self._loaded_at = datetime.now()
            logger.info(f"Plugin loaded: {self.id}")

        except Exception as e:
            self._state = PluginState.ERROR
            self._error = str(e)
            logger.error(f"Plugin load failed: {self.id} - {e}")
            raise

    async def _unload(self) -> None:
        """Internal unload method."""
        try:
            await self.on_unload()
        except Exception as e:
            logger.error(f"Plugin unload error: {self.id} - {e}")
        finally:
            self._state = PluginState.UNLOADED
            logger.info(f"Plugin unloaded: {self.id}")

    async def _start(self) -> None:
        """Internal start method."""
        if self._state != PluginState.LOADED:
            raise RuntimeError(f"Cannot start plugin in state: {self._state}")

        self._state = PluginState.STARTING

        try:
            await self.on_start()
            self._state = PluginState.RUNNING
            self._started_at = datetime.now()
            logger.info(f"Plugin started: {self.id}")

        except Exception as e:
            self._state = PluginState.ERROR
            self._error = str(e)
            logger.error(f"Plugin start failed: {self.id} - {e}")
            raise

    async def _stop(self) -> None:
        """Internal stop method."""
        if self._state != PluginState.RUNNING:
            return

        self._state = PluginState.STOPPING

        try:
            await self.on_stop()
        except Exception as e:
            logger.error(f"Plugin stop error: {self.id} - {e}")
        finally:
            self._state = PluginState.STOPPED
            logger.info(f"Plugin stopped: {self.id}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """Get plugin status."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "state": self._state.value,
            "loaded_at": self._loaded_at.isoformat() if self._loaded_at else None,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "error": self._error,
        }

    async def emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event to the event bus."""
        if self._event_bus:
            from nexus.core.events import EventType
            try:
                et = EventType(event_type)
                await self._event_bus.emit(et, data, source=self.id)
            except ValueError:
                logger.warning(f"Unknown event type: {event_type}")

    def log(self, level: str, message: str) -> None:
        """Log with plugin context."""
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[{self.id}] {message}")


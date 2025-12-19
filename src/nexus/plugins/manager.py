"""
Plugin manager.

Manages plugin lifecycle and orchestration.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from nexus.config import NexusConfig, get_config
from nexus.core.events import EventBus, get_event_bus
from nexus.plugins.base import Plugin
from nexus.plugins.hooks import HookRegistry, get_hook_registry
from nexus.plugins.loader import PluginLoader

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Central plugin management.

    Responsibilities:
    - Plugin discovery and loading
    - Lifecycle management (start/stop)
    - Hook registration
    - Dependency resolution
    """

    def __init__(
        self,
        config: NexusConfig | None = None,
        event_bus: EventBus | None = None,
        hook_registry: HookRegistry | None = None,
    ) -> None:
        self._config = config or get_config()
        self._event_bus = event_bus or get_event_bus()
        self._hooks = hook_registry or get_hook_registry()

        self._loader = PluginLoader()
        self._plugins: dict[str, Plugin] = {}
        self._plugin_configs: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    # =========================================================================
    # Plugin Loading
    # =========================================================================

    async def load(
        self,
        plugin_class: type[Plugin],
        config: dict[str, Any] | None = None,
    ) -> Plugin | None:
        """
        Load and initialize a plugin.

        Args:
            plugin_class: Plugin class to instantiate
            config: Plugin configuration

        Returns:
            Plugin instance or None on failure
        """
        async with self._lock:
            # Check if already loaded
            plugin_id = plugin_class.metadata.id
            if plugin_id in self._plugins:
                logger.warning(f"Plugin already loaded: {plugin_id}")
                return self._plugins[plugin_id]

            try:
                # Instantiate plugin
                plugin = plugin_class()

                # Load plugin
                await plugin._load(
                    config=config or {},
                    nexus_config=self._config,
                    event_bus=self._event_bus,
                )

                # Register hooks from decorated methods
                await self._register_hooks(plugin)

                self._plugins[plugin_id] = plugin
                self._plugin_configs[plugin_id] = config or {}

                logger.info(f"Plugin loaded: {plugin_id}")
                return plugin

            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_class.metadata.id}: {e}")
                return None

    async def load_from_path(
        self,
        path: Path,
        config: dict[str, Any] | None = None,
    ) -> Plugin | None:
        """Load plugin from file path."""
        plugin_class = self._loader.load_from_path(path)
        if plugin_class:
            return await self.load(plugin_class, config)
        return None

    async def load_from_module(
        self,
        module_name: str,
        config: dict[str, Any] | None = None,
    ) -> Plugin | None:
        """Load plugin from module name."""
        plugin_class = self._loader.load_from_module(module_name)
        if plugin_class:
            return await self.load(plugin_class, config)
        return None

    async def unload(self, plugin_id: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_id: Plugin to unload

        Returns:
            True if unloaded
        """
        async with self._lock:
            plugin = self._plugins.get(plugin_id)
            if not plugin:
                return False

            # Stop if running
            if plugin.is_running:
                await plugin._stop()

            # Unregister hooks
            await self._hooks.unregister_plugin(plugin_id)

            # Unload
            await plugin._unload()

            del self._plugins[plugin_id]
            self._plugin_configs.pop(plugin_id, None)

            logger.info(f"Plugin unloaded: {plugin_id}")
            return True

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self, plugin_id: str) -> bool:
        """
        Start a loaded plugin.

        Args:
            plugin_id: Plugin to start

        Returns:
            True if started
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        if plugin.is_running:
            return True

        try:
            await plugin._start()
            return True
        except Exception as e:
            logger.error(f"Failed to start plugin {plugin_id}: {e}")
            return False

    async def stop(self, plugin_id: str) -> bool:
        """
        Stop a running plugin.

        Args:
            plugin_id: Plugin to stop

        Returns:
            True if stopped
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False

        if not plugin.is_running:
            return True

        try:
            await plugin._stop()
            return True
        except Exception as e:
            logger.error(f"Failed to stop plugin {plugin_id}: {e}")
            return False

    async def start_all(self) -> dict[str, bool]:
        """Start all loaded plugins."""
        results = {}
        for plugin_id in self._plugins:
            results[plugin_id] = await self.start(plugin_id)
        return results

    async def stop_all(self) -> dict[str, bool]:
        """Stop all running plugins."""
        results = {}
        for plugin_id in list(self._plugins.keys()):
            results[plugin_id] = await self.stop(plugin_id)
        return results

    async def unload_all(self) -> None:
        """Unload all plugins."""
        for plugin_id in list(self._plugins.keys()):
            await self.unload(plugin_id)

    # =========================================================================
    # Hook Registration
    # =========================================================================

    async def _register_hooks(self, plugin: Plugin) -> None:
        """Register hooks from plugin methods."""
        for name in dir(plugin):
            if name.startswith("_"):
                continue

            method = getattr(plugin, name)
            if not callable(method):
                continue

            # Check for hook decorators
            if hasattr(method, "_hooks"):
                for hook_info in method._hooks:
                    await self._hooks.register(
                        hook_type=hook_info["type"],
                        handler=method,
                        plugin_id=plugin.id,
                        priority=hook_info["priority"],
                    )

    # =========================================================================
    # Queries
    # =========================================================================

    def get(self, plugin_id: str) -> Plugin | None:
        """Get plugin by ID."""
        return self._plugins.get(plugin_id)

    def get_all(self) -> list[Plugin]:
        """Get all loaded plugins."""
        return list(self._plugins.values())

    def get_running(self) -> list[Plugin]:
        """Get running plugins."""
        return [p for p in self._plugins.values() if p.is_running]

    def is_loaded(self, plugin_id: str) -> bool:
        """Check if plugin is loaded."""
        return plugin_id in self._plugins

    def is_running(self, plugin_id: str) -> bool:
        """Check if plugin is running."""
        plugin = self._plugins.get(plugin_id)
        return plugin.is_running if plugin else False

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get plugin manager statistics."""
        hook_count = await self._hooks.count()

        return {
            "loaded": len(self._plugins),
            "running": len(self.get_running()),
            "hooks_registered": hook_count,
            "plugins": [p.get_status() for p in self._plugins.values()],
        }


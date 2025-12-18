"""
Plugin loader.

Discovers and imports plugins from various sources.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Type

from nexus.plugins.base import Plugin, PluginMetadata

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Information about a discovered plugin."""

    path: Path
    module_name: str
    metadata: PluginMetadata | None = None
    plugin_class: Type[Plugin] | None = None
    error: str | None = None


class PluginLoader:
    """
    Plugin discovery and loading.

    Features:
    - Load from directories
    - Load from Python packages
    - Load single plugin files
    - Dependency resolution
    """

    def __init__(self, plugin_dirs: list[Path] | None = None) -> None:
        """
        Initialize plugin loader.

        Args:
            plugin_dirs: Directories to search for plugins
        """
        self._plugin_dirs = plugin_dirs or []
        self._discovered: dict[str, PluginInfo] = {}

    # =========================================================================
    # Discovery
    # =========================================================================

    def discover(self, directory: Path | None = None) -> list[PluginInfo]:
        """
        Discover plugins in directories.

        Args:
            directory: Specific directory to search (or use configured dirs)

        Returns:
            List of discovered plugin info
        """
        dirs = [directory] if directory else self._plugin_dirs
        discovered = []

        for dir_path in dirs:
            if not dir_path.exists():
                logger.warning(f"Plugin directory not found: {dir_path}")
                continue

            # Look for plugin packages (directories with __init__.py)
            for item in dir_path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    info = self._discover_package(item)
                    if info:
                        discovered.append(info)
                        self._discovered[info.module_name] = info

                # Look for single-file plugins
                elif item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                    info = self._discover_file(item)
                    if info:
                        discovered.append(info)
                        self._discovered[info.module_name] = info

        logger.info(f"Discovered {len(discovered)} plugins")
        return discovered

    def _discover_package(self, path: Path) -> PluginInfo | None:
        """Discover a plugin package."""
        module_name = f"nexus_plugins.{path.name}"

        try:
            # Try to import just to get metadata
            spec = importlib.util.spec_from_file_location(
                module_name,
                path / "__init__.py",
            )
            if not spec or not spec.loader:
                return None

            return PluginInfo(
                path=path,
                module_name=module_name,
            )

        except Exception as e:
            logger.warning(f"Failed to discover plugin {path}: {e}")
            return PluginInfo(
                path=path,
                module_name=module_name,
                error=str(e),
            )

    def _discover_file(self, path: Path) -> PluginInfo | None:
        """Discover a single-file plugin."""
        module_name = f"nexus_plugins.{path.stem}"

        return PluginInfo(
            path=path,
            module_name=module_name,
        )

    # =========================================================================
    # Loading
    # =========================================================================

    def load(self, info: PluginInfo) -> Type[Plugin] | None:
        """
        Load a plugin class from PluginInfo.

        Args:
            info: Plugin info from discovery

        Returns:
            Plugin class or None on error
        """
        if info.error:
            logger.error(f"Cannot load plugin with error: {info.error}")
            return None

        try:
            # Load module
            if info.path.is_dir():
                module = self._load_package(info.path, info.module_name)
            else:
                module = self._load_file(info.path, info.module_name)

            if not module:
                return None

            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                logger.warning(f"No Plugin subclass found in {info.module_name}")
                return None

            info.plugin_class = plugin_class
            info.metadata = plugin_class.metadata

            logger.info(f"Loaded plugin: {info.metadata.name} v{info.metadata.version}")
            return plugin_class

        except Exception as e:
            logger.error(f"Failed to load plugin {info.module_name}: {e}")
            info.error = str(e)
            return None

    def load_from_module(self, module_name: str) -> Type[Plugin] | None:
        """
        Load a plugin from an installed Python module.

        Args:
            module_name: Fully qualified module name

        Returns:
            Plugin class or None
        """
        try:
            module = importlib.import_module(module_name)
            return self._find_plugin_class(module)

        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            return None

    def load_from_path(self, path: Path) -> Type[Plugin] | None:
        """
        Load a plugin from a specific path.

        Args:
            path: Path to plugin file or directory

        Returns:
            Plugin class or None
        """
        if path.is_dir():
            info = self._discover_package(path)
        else:
            info = self._discover_file(path)

        if info:
            return self.load(info)
        return None

    def _load_package(self, path: Path, module_name: str) -> Any:
        """Load a plugin package."""
        # Add parent to sys.path if needed
        parent = path.parent
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))

        spec = importlib.util.spec_from_file_location(
            module_name,
            path / "__init__.py",
            submodule_search_locations=[str(path)],
        )

        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

    def _load_file(self, path: Path, module_name: str) -> Any:
        """Load a single-file plugin."""
        spec = importlib.util.spec_from_file_location(module_name, path)

        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

    def _find_plugin_class(self, module: Any) -> Type[Plugin] | None:
        """Find Plugin subclass in module."""
        for name in dir(module):
            obj = getattr(module, name)

            # Check if it's a class
            if not isinstance(obj, type):
                continue

            # Check if it's a Plugin subclass (but not Plugin itself)
            if issubclass(obj, Plugin) and obj is not Plugin:
                # Verify it has metadata
                if hasattr(obj, "metadata") and obj.metadata:
                    return obj

        return None

    # =========================================================================
    # Utilities
    # =========================================================================

    def get_discovered(self) -> dict[str, PluginInfo]:
        """Get all discovered plugins."""
        return dict(self._discovered)

    def reload(self, module_name: str) -> Type[Plugin] | None:
        """
        Reload a plugin module.

        Args:
            module_name: Module name to reload

        Returns:
            Reloaded plugin class or None
        """
        if module_name in sys.modules:
            try:
                module = importlib.reload(sys.modules[module_name])
                return self._find_plugin_class(module)
            except Exception as e:
                logger.error(f"Failed to reload {module_name}: {e}")

        return None


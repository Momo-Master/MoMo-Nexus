"""Plugin system for MoMo-Nexus."""

from nexus.plugins.base import (
    Plugin,
    PluginCapability,
    PluginMetadata,
    PluginState,
)
from nexus.plugins.hooks import (
    Hook,
    HookRegistry,
    HookType,
    hook,
)
from nexus.plugins.loader import PluginLoader
from nexus.plugins.manager import PluginManager

__all__ = [
    # Base
    "Plugin",
    "PluginMetadata",
    "PluginState",
    "PluginCapability",
    # Hooks
    "Hook",
    "HookType",
    "HookRegistry",
    "hook",
    # Loader
    "PluginLoader",
    # Manager
    "PluginManager",
]


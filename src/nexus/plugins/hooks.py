"""
Hook system for plugin extensibility.

Provides extension points for plugins to intercept and modify behavior.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HookType(str, Enum):
    """Types of hooks available."""

    # Message hooks
    MESSAGE_PRE_ROUTE = "message.pre_route"  # Before routing
    MESSAGE_POST_ROUTE = "message.post_route"  # After routing
    MESSAGE_PRE_SEND = "message.pre_send"  # Before sending
    MESSAGE_POST_SEND = "message.post_send"  # After sending
    MESSAGE_RECEIVED = "message.received"  # On message received
    MESSAGE_FILTER = "message.filter"  # Filter messages

    # Device hooks
    DEVICE_PRE_REGISTER = "device.pre_register"  # Before registration
    DEVICE_POST_REGISTER = "device.post_register"  # After registration
    DEVICE_AUTH = "device.auth"  # Authentication hook

    # Channel hooks
    CHANNEL_PRE_CONNECT = "channel.pre_connect"
    CHANNEL_POST_CONNECT = "channel.post_connect"
    CHANNEL_DISCONNECT = "channel.disconnect"

    # Alert hooks
    ALERT_CREATE = "alert.create"  # When alert is created
    ALERT_FILTER = "alert.filter"  # Filter alerts
    ALERT_NOTIFY = "alert.notify"  # Notification hook

    # Zone hooks
    ZONE_ENTER = "zone.enter"
    ZONE_EXIT = "zone.exit"

    # Security hooks
    SECURITY_PRE_ENCRYPT = "security.pre_encrypt"
    SECURITY_POST_DECRYPT = "security.post_decrypt"
    SECURITY_VERIFY = "security.verify"

    # System hooks
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_TICK = "system.tick"  # Periodic tick


# Type for hook handlers
HookHandler = Callable[..., Coroutine[Any, Any, Any]]


@dataclass
class Hook:
    """
    A registered hook.

    Attributes:
        hook_type: Type of hook
        handler: Handler function
        plugin_id: Plugin that registered the hook
        priority: Execution priority (lower = earlier)
        enabled: Whether hook is active
    """

    hook_type: HookType
    handler: HookHandler
    plugin_id: str
    priority: int = 50
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "Hook") -> bool:
        """Sort by priority."""
        return self.priority < other.priority


class HookRegistry:
    """
    Registry for plugin hooks.

    Manages hook registration and execution.
    """

    def __init__(self) -> None:
        self._hooks: dict[HookType, list[Hook]] = {}
        self._lock = asyncio.Lock()

    # =========================================================================
    # Registration
    # =========================================================================

    async def register(
        self,
        hook_type: HookType,
        handler: HookHandler,
        plugin_id: str,
        priority: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> Hook:
        """
        Register a hook handler.

        Args:
            hook_type: Type of hook
            handler: Handler function
            plugin_id: Plugin ID
            priority: Execution priority (0-100, lower = earlier)
            metadata: Additional metadata

        Returns:
            Registered hook
        """
        hook = Hook(
            hook_type=hook_type,
            handler=handler,
            plugin_id=plugin_id,
            priority=priority,
            metadata=metadata or {},
        )

        async with self._lock:
            if hook_type not in self._hooks:
                self._hooks[hook_type] = []

            self._hooks[hook_type].append(hook)
            self._hooks[hook_type].sort()  # Sort by priority

        logger.debug(f"Hook registered: {hook_type.value} by {plugin_id}")
        return hook

    async def unregister(self, hook: Hook) -> None:
        """Unregister a hook."""
        async with self._lock:
            if hook.hook_type in self._hooks:
                try:
                    self._hooks[hook.hook_type].remove(hook)
                except ValueError:
                    pass

    async def unregister_plugin(self, plugin_id: str) -> int:
        """
        Unregister all hooks for a plugin.

        Args:
            plugin_id: Plugin ID

        Returns:
            Number of hooks removed
        """
        count = 0

        async with self._lock:
            for hook_type in self._hooks:
                original_len = len(self._hooks[hook_type])
                self._hooks[hook_type] = [
                    h for h in self._hooks[hook_type]
                    if h.plugin_id != plugin_id
                ]
                count += original_len - len(self._hooks[hook_type])

        logger.debug(f"Unregistered {count} hooks for plugin {plugin_id}")
        return count

    # =========================================================================
    # Execution
    # =========================================================================

    async def call(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> list[Any]:
        """
        Call all hooks of a type.

        Args:
            hook_type: Type of hook to call
            *args: Arguments to pass to handlers
            **kwargs: Keyword arguments to pass

        Returns:
            List of results from all handlers
        """
        async with self._lock:
            hooks = list(self._hooks.get(hook_type, []))

        results = []
        for hook in hooks:
            if not hook.enabled:
                continue

            try:
                result = await hook.handler(*args, **kwargs)
                results.append(result)

            except Exception as e:
                logger.error(
                    f"Hook error: {hook_type.value} ({hook.plugin_id}): {e}"
                )

        return results

    async def call_filter(
        self,
        hook_type: HookType,
        value: T,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Call filter hooks that transform a value.

        Each hook receives the value and can modify it.
        The final value is returned.

        Args:
            hook_type: Type of hook
            value: Value to filter
            *args: Additional arguments
            **kwargs: Keyword arguments

        Returns:
            Filtered value
        """
        async with self._lock:
            hooks = list(self._hooks.get(hook_type, []))

        for hook in hooks:
            if not hook.enabled:
                continue

            try:
                result = await hook.handler(value, *args, **kwargs)
                if result is not None:
                    value = result

            except Exception as e:
                logger.error(
                    f"Filter hook error: {hook_type.value} ({hook.plugin_id}): {e}"
                )

        return value

    async def call_first(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> Any | None:
        """
        Call hooks until one returns a truthy value.

        Args:
            hook_type: Type of hook
            *args: Arguments
            **kwargs: Keyword arguments

        Returns:
            First truthy result or None
        """
        async with self._lock:
            hooks = list(self._hooks.get(hook_type, []))

        for hook in hooks:
            if not hook.enabled:
                continue

            try:
                result = await hook.handler(*args, **kwargs)
                if result:
                    return result

            except Exception as e:
                logger.error(
                    f"Hook error: {hook_type.value} ({hook.plugin_id}): {e}"
                )

        return None

    async def call_all_or_none(
        self,
        hook_type: HookType,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """
        Call all hooks, return False if any returns False.

        Useful for validation hooks.

        Args:
            hook_type: Type of hook
            *args: Arguments
            **kwargs: Keyword arguments

        Returns:
            True if all hooks return True (or no hooks)
        """
        async with self._lock:
            hooks = list(self._hooks.get(hook_type, []))

        for hook in hooks:
            if not hook.enabled:
                continue

            try:
                result = await hook.handler(*args, **kwargs)
                if result is False:
                    return False

            except Exception as e:
                logger.error(
                    f"Hook error: {hook_type.value} ({hook.plugin_id}): {e}"
                )
                return False

        return True

    # =========================================================================
    # Queries
    # =========================================================================

    async def get_hooks(self, hook_type: HookType) -> list[Hook]:
        """Get all hooks of a type."""
        async with self._lock:
            return list(self._hooks.get(hook_type, []))

    async def get_all_hooks(self) -> dict[HookType, list[Hook]]:
        """Get all registered hooks."""
        async with self._lock:
            return {k: list(v) for k, v in self._hooks.items()}

    async def count(self, hook_type: HookType | None = None) -> int:
        """Count registered hooks."""
        async with self._lock:
            if hook_type:
                return len(self._hooks.get(hook_type, []))
            return sum(len(hooks) for hooks in self._hooks.values())


# Global hook registry
_hook_registry: HookRegistry | None = None


def get_hook_registry() -> HookRegistry:
    """Get the global hook registry."""
    global _hook_registry
    if _hook_registry is None:
        _hook_registry = HookRegistry()
    return _hook_registry


# =========================================================================
# Decorator
# =========================================================================


def hook(
    hook_type: HookType,
    priority: int = 50,
) -> Callable[[HookHandler], HookHandler]:
    """
    Decorator to mark a method as a hook handler.

    Usage:
        class MyPlugin(Plugin):
            @hook(HookType.MESSAGE_RECEIVED)
            async def on_message(self, message):
                ...

    Args:
        hook_type: Type of hook
        priority: Execution priority

    Returns:
        Decorated function
    """

    def decorator(func: HookHandler) -> HookHandler:
        # Mark function with hook metadata
        if not hasattr(func, "_hooks"):
            func._hooks = []  # type: ignore

        func._hooks.append({  # type: ignore
            "type": hook_type,
            "priority": priority,
        })

        return func

    return decorator


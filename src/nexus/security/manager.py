"""
Security Manager.

Central security orchestration for MoMo-Nexus.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from typing import Any

from nexus.config import NexusConfig, get_config
from nexus.core.events import EventBus, get_event_bus
from nexus.domain.models import Message
from nexus.security.crypto import CryptoProvider, derive_key, generate_key
from nexus.security.envelope import EnvelopeBuilder, SecureEnvelope, SecurityLevel
from nexus.security.hmac import HMACProvider
from nexus.security.replay import ReplayGuard

logger = logging.getLogger(__name__)


@dataclass
class DeviceKeys:
    """Key material for a device."""

    device_id: str
    hmac_key: bytes
    encryption_key: bytes | None = None
    session_id: str = field(default_factory=lambda: secrets.token_hex(16))
    created_at: int = field(default_factory=lambda: int(__import__("time").time()))


class SecurityManager:
    """
    Central security manager.

    Responsibilities:
    - Key management
    - Message signing/verification
    - Encryption/decryption
    - Replay protection
    - Device authentication
    """

    def __init__(
        self,
        config: NexusConfig | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._config = config or get_config()
        self._event_bus = event_bus or get_event_bus()

        # Master key (should be loaded from secure storage)
        self._master_key = self._load_master_key()

        # Derived keys
        self._hmac_key = derive_key(self._master_key, "hmac")
        self._encryption_key = derive_key(self._master_key, "encryption")

        # Device keys
        self._device_keys: dict[str, DeviceKeys] = {}
        self._lock = asyncio.Lock()

        # Components
        self._hmac = HMACProvider(self._hmac_key)
        self._crypto = CryptoProvider(self._encryption_key)
        self._replay = ReplayGuard(
            window_seconds=self._config.security.replay_window,
            max_nonces=self._config.security.max_nonces,
        )
        self._envelope = EnvelopeBuilder(self._hmac_key, self._encryption_key)

        # Default security level
        self._default_level = SecurityLevel(self._config.security.default_level)

        self._running = False

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> None:
        """Start security manager."""
        if self._running:
            return

        self._running = True
        await self._replay.start()
        logger.info("Security manager started")

    async def stop(self) -> None:
        """Stop security manager."""
        self._running = False
        await self._replay.stop()
        logger.info("Security manager stopped")

    # =========================================================================
    # Key Management
    # =========================================================================

    def _load_master_key(self) -> bytes:
        """Load or generate master key."""
        key_hex = self._config.security.master_key

        if key_hex:
            return bytes.fromhex(key_hex)
        else:
            # Generate ephemeral key (not for production!)
            key = generate_key()
            logger.warning("Using ephemeral master key - configure security.master_key!")
            return key

    async def register_device_key(
        self,
        device_id: str,
        pre_shared_key: bytes | None = None,
    ) -> DeviceKeys:
        """
        Register or derive keys for a device.

        Args:
            device_id: Device identifier
            pre_shared_key: Optional pre-shared key

        Returns:
            Device key material
        """
        async with self._lock:
            if device_id in self._device_keys:
                return self._device_keys[device_id]

            # Derive keys from master or PSK
            base_key = pre_shared_key or self._master_key
            hmac_key = derive_key(base_key, f"hmac:{device_id}")
            enc_key = derive_key(base_key, f"enc:{device_id}")

            keys = DeviceKeys(
                device_id=device_id,
                hmac_key=hmac_key,
                encryption_key=enc_key,
            )

            self._device_keys[device_id] = keys
            logger.debug(f"Registered keys for device: {device_id}")

            return keys

    async def get_device_keys(self, device_id: str) -> DeviceKeys | None:
        """Get keys for a device."""
        async with self._lock:
            return self._device_keys.get(device_id)

    async def rotate_device_keys(self, device_id: str) -> DeviceKeys | None:
        """Rotate keys for a device."""
        async with self._lock:
            if device_id not in self._device_keys:
                return None

            old_keys = self._device_keys[device_id]

            # Derive new keys from old keys + new session
            new_session = secrets.token_hex(16)
            new_hmac = derive_key(old_keys.hmac_key, f"rotate:{new_session}")
            new_enc = derive_key(
                old_keys.encryption_key or old_keys.hmac_key,
                f"rotate:{new_session}",
            )

            keys = DeviceKeys(
                device_id=device_id,
                hmac_key=new_hmac,
                encryption_key=new_enc,
                session_id=new_session,
            )

            self._device_keys[device_id] = keys
            logger.info(f"Rotated keys for device: {device_id}")

            return keys

    # =========================================================================
    # Message Security
    # =========================================================================

    async def secure_message(
        self,
        message: Message,
        level: SecurityLevel | None = None,
    ) -> SecureEnvelope:
        """
        Secure a message for transmission.

        Args:
            message: Message to secure
            level: Security level (uses default if not specified)

        Returns:
            Secure envelope
        """
        level = level or self._default_level

        # Get device-specific envelope builder if available
        builder = self._envelope
        if message.dst:
            keys = await self.get_device_keys(message.dst)
            if keys:
                builder = EnvelopeBuilder(keys.hmac_key, keys.encryption_key)

        # Convert message to payload
        payload = message.model_dump()

        # Wrap in envelope
        envelope = builder.wrap(payload, level)

        logger.debug(f"Secured message {message.id} with level {level.value}")
        return envelope

    async def verify_message(
        self,
        envelope: SecureEnvelope,
        device_id: str | None = None,
    ) -> tuple[bool, Message | None]:
        """
        Verify and unwrap a secure message.

        Args:
            envelope: Received envelope
            device_id: Expected device ID (for key lookup)

        Returns:
            Tuple of (is_valid, message)
        """
        # Check replay
        is_fresh = await self._replay.check_nonce(
            envelope.nonce,
            envelope.ts,
            device_id,
        )
        if not is_fresh:
            logger.warning(f"Replay detected for nonce {envelope.nonce[:16]}...")
            return False, None

        # Get device-specific envelope builder if available
        builder = self._envelope
        if device_id:
            keys = await self.get_device_keys(device_id)
            if keys:
                builder = EnvelopeBuilder(keys.hmac_key, keys.encryption_key)

        try:
            # Unwrap and verify
            payload = builder.unwrap(envelope, verify=True)

            # Convert to message
            message = Message.model_validate(payload)

            logger.debug(f"Verified message {message.id} from envelope")
            return True, message

        except ValueError as e:
            logger.warning(f"Message verification failed: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Message unwrap error: {e}")
            return False, None

    async def sign_data(
        self,
        data: dict[str, Any],
        device_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Sign arbitrary data.

        Args:
            data: Data to sign
            device_id: Optional device for key lookup

        Returns:
            Signed data with signature fields
        """
        hmac = self._hmac
        if device_id:
            keys = await self.get_device_keys(device_id)
            if keys:
                hmac = HMACProvider(keys.hmac_key)

        return hmac.sign_dict(data)

    async def verify_data(
        self,
        data: dict[str, Any],
        device_id: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Verify signed data.

        Args:
            data: Signed data
            device_id: Optional device for key lookup

        Returns:
            Tuple of (is_valid, original_data)
        """
        hmac = self._hmac
        if device_id:
            keys = await self.get_device_keys(device_id)
            if keys:
                hmac = HMACProvider(keys.hmac_key)

        return hmac.verify_dict(data)

    # =========================================================================
    # Encryption Helpers
    # =========================================================================

    async def encrypt(
        self,
        data: bytes,
        device_id: str | None = None,
    ) -> bytes:
        """Encrypt data."""
        crypto = self._crypto
        if device_id:
            keys = await self.get_device_keys(device_id)
            if keys and keys.encryption_key:
                crypto = CryptoProvider(keys.encryption_key)

        payload = crypto.encrypt(data)
        return payload.to_bytes()

    async def decrypt(
        self,
        data: bytes,
        device_id: str | None = None,
    ) -> bytes:
        """Decrypt data."""
        from nexus.security.crypto import EncryptedPayload

        crypto = self._crypto
        if device_id:
            keys = await self.get_device_keys(device_id)
            if keys and keys.encryption_key:
                crypto = CryptoProvider(keys.encryption_key)

        payload = EncryptedPayload.from_bytes(data)
        return crypto.decrypt(payload)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> dict[str, Any]:
        """Get security statistics."""
        replay_stats = await self._replay.get_stats()

        async with self._lock:
            device_count = len(self._device_keys)

        return {
            "running": self._running,
            "default_level": self._default_level.value,
            "devices_with_keys": device_count,
            "replay_guard": replay_stats,
        }


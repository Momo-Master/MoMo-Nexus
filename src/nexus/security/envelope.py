"""
Secure message envelope.

Wraps messages with authentication and optional encryption.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from nexus.security.crypto import CryptoProvider, EncryptedPayload
from nexus.security.hmac import HMACProvider


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class SecurityLevel(str, Enum):
    """Message security level."""

    NONE = "none"  # No security (testing only)
    SIGNED = "signed"  # HMAC authentication only
    ENCRYPTED = "encrypted"  # Signed + encrypted


@dataclass
class SecureEnvelope:
    """
    Secure message envelope.

    Structure:
        - ver: Protocol version
        - lvl: Security level
        - ts: Timestamp
        - nonce: Unique nonce
        - payload: Message payload (encrypted or plain)
        - sig: HMAC signature
    """

    ver: int = 1
    lvl: SecurityLevel = SecurityLevel.SIGNED
    ts: int = field(default_factory=lambda: int(time.time()))
    nonce: str = field(default_factory=lambda: secrets.token_hex(16))
    payload: str = ""  # JSON payload or base64 encrypted
    sig: str = ""  # Base64 HMAC signature

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ver": self.ver,
            "lvl": self.lvl.value,
            "ts": self.ts,
            "nonce": self.nonce,
            "payload": self.payload,
            "sig": self.sig,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SecureEnvelope:
        """Create from dictionary."""
        return cls(
            ver=data.get("ver", 1),
            lvl=SecurityLevel(data.get("lvl", "signed")),
            ts=data.get("ts", 0),
            nonce=data.get("nonce", ""),
            payload=data.get("payload", ""),
            sig=data.get("sig", ""),
        )

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), separators=(",", ":"))

    @classmethod
    def from_json(cls, data: str) -> SecureEnvelope:
        """Deserialize from JSON."""
        return cls.from_dict(json.loads(data))

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        return self.to_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> SecureEnvelope:
        """Deserialize from bytes."""
        return cls.from_json(data.decode("utf-8"))


class EnvelopeBuilder:
    """
    Builds secure envelopes.

    Handles signing and encryption.
    """

    def __init__(
        self,
        hmac_key: bytes,
        encryption_key: bytes | None = None,
    ) -> None:
        """
        Initialize envelope builder.

        Args:
            hmac_key: Key for HMAC signing
            encryption_key: Key for encryption (optional)
        """
        self._hmac = HMACProvider(hmac_key)
        self._crypto = CryptoProvider(encryption_key) if encryption_key else None

    def wrap(
        self,
        payload: dict[str, Any],
        level: SecurityLevel = SecurityLevel.SIGNED,
    ) -> SecureEnvelope:
        """
        Wrap payload in secure envelope.

        Args:
            payload: Message payload
            level: Security level

        Returns:
            Secure envelope
        """
        envelope = SecureEnvelope(lvl=level)

        # Serialize payload
        payload_json = json.dumps(payload, separators=(",", ":"), default=_json_serializer)

        # Encrypt if required
        if level == SecurityLevel.ENCRYPTED and self._crypto:
            # Associated data: version + level + timestamp + nonce
            ad = f"{envelope.ver}:{level.value}:{envelope.ts}:{envelope.nonce}"
            encrypted = self._crypto.encrypt(
                payload_json.encode("utf-8"),
                ad.encode("utf-8"),
            )
            envelope.payload = encrypted.to_base64()
        else:
            envelope.payload = payload_json

        # Sign the envelope
        if level != SecurityLevel.NONE:
            sig_data = self._signing_data(envelope)
            message = self._hmac.sign(sig_data, envelope.ts, envelope.nonce)
            from base64 import b64encode
            envelope.sig = b64encode(message.signature).decode("ascii")

        return envelope

    def unwrap(
        self,
        envelope: SecureEnvelope,
        verify: bool = True,
    ) -> dict[str, Any]:
        """
        Unwrap secure envelope.

        Args:
            envelope: Secure envelope
            verify: Whether to verify signature

        Returns:
            Original payload

        Raises:
            ValueError: If verification fails
        """
        # Verify signature
        if verify and envelope.lvl != SecurityLevel.NONE and not self.verify(envelope):
            raise ValueError("Envelope signature verification failed")

        # Decrypt if needed
        if envelope.lvl == SecurityLevel.ENCRYPTED and self._crypto:
            try:
                encrypted = EncryptedPayload.from_base64(envelope.payload)
                ad = f"{envelope.ver}:{envelope.lvl.value}:{envelope.ts}:{envelope.nonce}"
                plaintext = self._crypto.decrypt(encrypted, ad.encode("utf-8"))
                return json.loads(plaintext.decode("utf-8"))
            except Exception as e:
                raise ValueError(f"Decryption failed: {e}")
        else:
            return json.loads(envelope.payload)

    def verify(self, envelope: SecureEnvelope) -> bool:
        """
        Verify envelope signature.

        Args:
            envelope: Envelope to verify

        Returns:
            True if signature is valid
        """
        if envelope.lvl == SecurityLevel.NONE:
            return True

        if not envelope.sig:
            return False

        from base64 import b64decode

        from nexus.security.hmac import AuthenticatedMessage

        sig_data = self._signing_data(envelope)
        message = AuthenticatedMessage(
            payload=sig_data,
            signature=b64decode(envelope.sig),
            timestamp=envelope.ts,
            nonce=envelope.nonce,
        )

        return self._hmac.verify(message)

    def _signing_data(self, envelope: SecureEnvelope) -> bytes:
        """Create data to sign."""
        # Sign: version || level || timestamp || nonce || payload
        return (
            f"{envelope.ver}:{envelope.lvl.value}:{envelope.ts}:{envelope.nonce}:"
            f"{envelope.payload}"
        ).encode()


def wrap_message(
    payload: dict[str, Any],
    hmac_key: bytes,
    encryption_key: bytes | None = None,
    level: SecurityLevel = SecurityLevel.SIGNED,
) -> SecureEnvelope:
    """Quick message wrapping."""
    builder = EnvelopeBuilder(hmac_key, encryption_key)
    return builder.wrap(payload, level)


def unwrap_message(
    envelope: SecureEnvelope,
    hmac_key: bytes,
    encryption_key: bytes | None = None,
) -> dict[str, Any]:
    """Quick message unwrapping."""
    builder = EnvelopeBuilder(hmac_key, encryption_key)
    return builder.unwrap(envelope)


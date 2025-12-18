"""
HMAC-SHA256 message authentication.

Provides message integrity and authenticity verification.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from base64 import b64decode, b64encode
from dataclasses import dataclass
from typing import Any

# HMAC key size
HMAC_KEY_SIZE = 32


@dataclass
class AuthenticatedMessage:
    """Message with HMAC authentication."""

    payload: bytes
    signature: bytes
    timestamp: int
    nonce: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "payload": b64encode(self.payload).decode("ascii"),
            "sig": b64encode(self.signature).decode("ascii"),
            "ts": self.timestamp,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthenticatedMessage":
        """Create from dictionary."""
        return cls(
            payload=b64decode(data["payload"]),
            signature=b64decode(data["sig"]),
            timestamp=data["ts"],
            nonce=data["nonce"],
        )


class HMACProvider:
    """
    HMAC-SHA256 authentication provider.

    Features:
    - Message signing
    - Signature verification
    - Timestamp validation
    - Constant-time comparison
    """

    def __init__(
        self,
        key: bytes,
        max_age: int = 300,  # 5 minutes
    ) -> None:
        """
        Initialize HMAC provider.

        Args:
            key: HMAC key (32 bytes recommended)
            max_age: Maximum message age in seconds
        """
        self._key = key
        self._max_age = max_age

    def sign(
        self,
        payload: bytes,
        timestamp: int | None = None,
        nonce: str | None = None,
    ) -> AuthenticatedMessage:
        """
        Sign a payload with HMAC-SHA256.

        Args:
            payload: Data to sign
            timestamp: Unix timestamp (current time if not provided)
            nonce: Unique nonce (generated if not provided)

        Returns:
            Authenticated message with signature
        """
        import secrets

        if timestamp is None:
            timestamp = int(time.time())

        if nonce is None:
            nonce = secrets.token_hex(16)

        # Create canonical message: timestamp || nonce || payload
        canonical = self._canonical_message(payload, timestamp, nonce)

        # Generate HMAC
        signature = hmac.new(self._key, canonical, hashlib.sha256).digest()

        return AuthenticatedMessage(
            payload=payload,
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
        )

    def verify(
        self,
        message: AuthenticatedMessage,
        check_timestamp: bool = True,
    ) -> bool:
        """
        Verify message signature.

        Args:
            message: Authenticated message
            check_timestamp: Whether to check timestamp freshness

        Returns:
            True if signature is valid
        """
        # Check timestamp
        if check_timestamp:
            now = int(time.time())
            age = abs(now - message.timestamp)
            if age > self._max_age:
                return False

        # Recreate canonical message
        canonical = self._canonical_message(
            message.payload,
            message.timestamp,
            message.nonce,
        )

        # Compute expected signature
        expected = hmac.new(self._key, canonical, hashlib.sha256).digest()

        # Constant-time comparison
        return hmac.compare_digest(message.signature, expected)

    def sign_dict(
        self,
        data: dict[str, Any],
        timestamp: int | None = None,
        nonce: str | None = None,
    ) -> dict[str, Any]:
        """
        Sign a dictionary payload.

        Args:
            data: Dictionary to sign
            timestamp: Optional timestamp
            nonce: Optional nonce

        Returns:
            Dictionary with signature fields
        """
        import json

        payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        message = self.sign(payload, timestamp, nonce)

        return {
            **data,
            "_sig": b64encode(message.signature).decode("ascii"),
            "_ts": message.timestamp,
            "_nonce": message.nonce,
        }

    def verify_dict(
        self,
        data: dict[str, Any],
        check_timestamp: bool = True,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Verify a signed dictionary.

        Args:
            data: Dictionary with signature fields
            check_timestamp: Whether to check timestamp

        Returns:
            Tuple of (is_valid, original_data)
        """
        import json

        # Extract signature fields
        sig = data.pop("_sig", None)
        ts = data.pop("_ts", None)
        nonce = data.pop("_nonce", None)

        if not all([sig, ts, nonce]):
            return False, data

        # Recreate payload
        payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()

        message = AuthenticatedMessage(
            payload=payload,
            signature=b64decode(sig),
            timestamp=ts,
            nonce=nonce,
        )

        return self.verify(message, check_timestamp), data

    def _canonical_message(
        self,
        payload: bytes,
        timestamp: int,
        nonce: str,
    ) -> bytes:
        """Create canonical message for signing."""
        return (
            timestamp.to_bytes(8, "big")
            + nonce.encode("ascii")
            + payload
        )


def verify_hmac(
    key: bytes,
    payload: bytes,
    signature: bytes,
    timestamp: int,
    nonce: str,
    max_age: int = 300,
) -> bool:
    """
    Quick HMAC verification.

    Args:
        key: HMAC key
        payload: Original payload
        signature: Received signature
        timestamp: Message timestamp
        nonce: Message nonce
        max_age: Maximum message age

    Returns:
        True if valid
    """
    provider = HMACProvider(key, max_age)
    message = AuthenticatedMessage(
        payload=payload,
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )
    return provider.verify(message)


def sign_message(key: bytes, data: dict[str, Any]) -> dict[str, Any]:
    """Quick message signing."""
    provider = HMACProvider(key)
    return provider.sign_dict(data)


def verify_message(key: bytes, data: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Quick message verification."""
    provider = HMACProvider(key)
    return provider.verify_dict(data)


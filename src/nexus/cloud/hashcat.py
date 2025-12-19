"""
Hashcat Cloud Client.
~~~~~~~~~~~~~~~~~~~~~

Client for GPU-accelerated password cracking on cloud infrastructure.
Supports self-hosted VPS, Vast.ai, RunPod, or OnlineHashCrack API.
"""

from __future__ import annotations

import asyncio
import logging
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Crack job status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HashType(int, Enum):
    """Hashcat hash types (mode)."""
    WPA_PMKID = 22000      # WPA-PBKDF2-PMKID+EAPOL
    WPA_EAPOL = 22001      # WPA-PBKDF2-EAPOL (deprecated)
    WPA2 = 2500            # WPA/WPA2 (legacy)
    NTLM = 1000            # NTLM
    MD5 = 0                # MD5
    SHA1 = 100             # SHA1
    SHA256 = 1400          # SHA-256
    BCRYPT = 3200          # bcrypt


@dataclass
class CrackJob:
    """Crack job definition."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Target
    hash_type: HashType = HashType.WPA_PMKID
    hash_data: str = ""           # Hash or path to hash file
    hash_file: Path | None = None # Local file path
    
    # Attack settings
    attack_mode: int = 0          # 0=straight, 3=brute-force, 6=hybrid
    wordlist: str = "rockyou.txt"
    rules: list[str] = field(default_factory=list)
    mask: str | None = None       # For brute-force
    
    # Metadata
    ssid: str | None = None
    bssid: str | None = None
    device_id: str | None = None
    
    # Status
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Progress
    progress: float = 0.0         # 0-100
    speed: str = ""               # e.g., "500 MH/s"
    eta: str = ""                 # e.g., "2h 30m"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "hash_type": self.hash_type.value,
            "attack_mode": self.attack_mode,
            "wordlist": self.wordlist,
            "ssid": self.ssid,
            "bssid": self.bssid,
            "device_id": self.device_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
        }


@dataclass
class CrackResult:
    """Crack result."""
    
    job_id: str
    success: bool
    password: str | None = None
    
    # Stats
    duration_seconds: int = 0
    hashes_tried: int = 0
    speed_avg: str = ""
    
    # Error info
    error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "success": self.success,
            "password": self.password,
            "duration_seconds": self.duration_seconds,
            "hashes_tried": self.hashes_tried,
            "error": self.error,
        }


@dataclass
class CloudConfig:
    """Cloud hashcat configuration."""
    
    enabled: bool = False
    
    # Provider
    provider: str = "self_hosted"  # self_hosted, vast_ai, runpod, online_hashcrack
    
    # Self-hosted VPS
    url: str = "http://hashcat.local:8080"
    api_key: str = ""
    
    # Cloud providers (Vast.ai, RunPod)
    cloud_api_key: str = ""
    gpu_type: str = "rtx3090"      # Preferred GPU
    max_cost_per_hour: float = 1.0
    
    # Wordlists (on cloud)
    default_wordlist: str = "rockyou.txt"
    custom_wordlists: list[str] = field(default_factory=list)
    
    # Limits
    max_concurrent_jobs: int = 3
    job_timeout_hours: int = 24
    
    # Retry
    retry_count: int = 3
    retry_delay: float = 5.0


class HashcatCloudClient:
    """
    Client for cloud-based Hashcat cracking.
    
    Supports multiple backends:
    - Self-hosted VPS with Hashcat API
    - Vast.ai / RunPod (GPU rental)
    - OnlineHashCrack (pay-per-crack)
    
    Example:
        >>> client = HashcatCloudClient(CloudConfig(
        ...     enabled=True,
        ...     url="http://hashcat-vps:8080",
        ...     api_key="xxx"
        ... ))
        >>> await client.connect()
        >>> 
        >>> job = await client.submit_job(CrackJob(
        ...     hash_type=HashType.WPA_PMKID,
        ...     hash_file=Path("capture.22000"),
        ...     ssid="TargetWiFi"
        ... ))
        >>> 
        >>> # Check status
        >>> status = await client.get_job_status(job.id)
        >>> print(f"Progress: {status.progress}%")
        >>> 
        >>> # Wait for result
        >>> result = await client.wait_for_result(job.id)
        >>> if result.success:
        ...     print(f"Password: {result.password}")
    """
    
    def __init__(self, config: CloudConfig):
        """
        Initialize Hashcat cloud client.
        
        Args:
            config: Cloud configuration
        """
        self.config = config
        self._session: aiohttp.ClientSession | None = None
        self._connected = False
        
        # Local job tracking
        self._jobs: dict[str, CrackJob] = {}
        self._results: dict[str, CrackResult] = {}
        
        # Mock mode (no real VPS)
        self._mock_mode = False
    
    # ==================== Connection ====================
    
    async def connect(self) -> bool:
        """
        Connect to cloud cracking service.
        
        Returns:
            True if connected (or mock mode enabled)
        """
        if not self.config.enabled:
            logger.info("Cloud hashcat disabled")
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
                    logger.info(f"Connected to Hashcat cloud: {data.get('version', 'unknown')}")
                    self._connected = True
                    return True
                    
        except aiohttp.ClientError as e:
            logger.warning(f"Cloud hashcat not available: {e}")
            logger.info("Enabling mock mode for development")
            self._mock_mode = True
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to cloud hashcat: {e}")
            self._mock_mode = True
            self._connected = True
            return True
        
        return False
    
    async def disconnect(self) -> None:
        """Disconnect from cloud service."""
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
    
    # ==================== Job Management ====================
    
    async def submit_job(self, job: CrackJob) -> CrackJob:
        """
        Submit cracking job to cloud.
        
        Args:
            job: Crack job definition
            
        Returns:
            Updated job with ID and status
        """
        # Read hash file if provided
        if job.hash_file and job.hash_file.exists():
            job.hash_data = job.hash_file.read_text().strip()
        
        if not job.hash_data:
            raise ValueError("No hash data provided")
        
        # Store locally
        self._jobs[job.id] = job
        
        if self._mock_mode:
            # Mock: simulate job submission
            job.status = JobStatus.QUEUED
            logger.info(f"[MOCK] Job {job.id} queued for cracking")
            
            # Start mock cracking in background
            asyncio.create_task(self._mock_crack(job))
            return job
        
        # Real API call
        try:
            payload = {
                "hash_type": job.hash_type.value,
                "hash_data": job.hash_data,
                "attack_mode": job.attack_mode,
                "wordlist": job.wordlist,
                "rules": job.rules,
                "mask": job.mask,
                "metadata": {
                    "ssid": job.ssid,
                    "bssid": job.bssid,
                    "device_id": job.device_id,
                },
            }
            
            async with self._session.post(
                f"{self.config.url}/jobs",
                json=payload
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    job.id = data.get("id", job.id)
                    job.status = JobStatus(data.get("status", "queued"))
                    logger.info(f"Job {job.id} submitted to cloud")
                else:
                    text = await resp.text()
                    logger.error(f"Job submission failed: {resp.status} - {text}")
                    job.status = JobStatus.FAILED
                    
        except Exception as e:
            logger.error(f"Job submission error: {e}")
            job.status = JobStatus.FAILED
        
        return job
    
    async def get_job_status(self, job_id: str) -> CrackJob | None:
        """
        Get job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            Updated job or None if not found
        """
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        if self._mock_mode:
            return job
        
        # Real API call
        try:
            async with self._session.get(
                f"{self.config.url}/jobs/{job_id}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    job.status = JobStatus(data.get("status", job.status.value))
                    job.progress = data.get("progress", 0)
                    job.speed = data.get("speed", "")
                    job.eta = data.get("eta", "")
                    
        except Exception as e:
            logger.error(f"Status check error: {e}")
        
        return job
    
    async def get_result(self, job_id: str) -> CrackResult | None:
        """
        Get crack result.
        
        Args:
            job_id: Job ID
            
        Returns:
            Result or None if not complete
        """
        # Check cache
        if job_id in self._results:
            return self._results[job_id]
        
        job = self._jobs.get(job_id)
        if not job or job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
            return None
        
        if self._mock_mode:
            return self._results.get(job_id)
        
        # Real API call
        try:
            async with self._session.get(
                f"{self.config.url}/jobs/{job_id}/result"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = CrackResult(
                        job_id=job_id,
                        success=data.get("success", False),
                        password=data.get("password"),
                        duration_seconds=data.get("duration", 0),
                        hashes_tried=data.get("hashes_tried", 0),
                        error=data.get("error"),
                    )
                    self._results[job_id] = result
                    return result
                    
        except Exception as e:
            logger.error(f"Result fetch error: {e}")
        
        return None
    
    async def wait_for_result(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        timeout: float = 3600.0,
    ) -> CrackResult | None:
        """
        Wait for job completion and return result.
        
        Args:
            job_id: Job ID
            poll_interval: Status check interval in seconds
            timeout: Maximum wait time in seconds
            
        Returns:
            Result or None on timeout
        """
        start = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed > timeout:
                logger.warning(f"Job {job_id} timed out after {timeout}s")
                return None
            
            job = await self.get_job_status(job_id)
            if not job:
                return None
            
            if job.status == JobStatus.COMPLETED:
                return await self.get_result(job_id)
            elif job.status == JobStatus.FAILED:
                return CrackResult(
                    job_id=job_id,
                    success=False,
                    error="Job failed",
                )
            
            await asyncio.sleep(poll_interval)
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled
        """
        job = self._jobs.get(job_id)
        if not job:
            return False
        
        if self._mock_mode:
            job.status = JobStatus.CANCELLED
            return True
        
        try:
            async with self._session.delete(
                f"{self.config.url}/jobs/{job_id}"
            ) as resp:
                if resp.status == 200:
                    job.status = JobStatus.CANCELLED
                    return True
        except Exception as e:
            logger.error(f"Cancel error: {e}")
        
        return False
    
    async def list_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 100,
    ) -> list[CrackJob]:
        """
        List jobs.
        
        Args:
            status: Filter by status
            limit: Max results
            
        Returns:
            List of jobs
        """
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return jobs[:limit]
    
    # ==================== Convenience Methods ====================
    
    async def crack_handshake(
        self,
        hash_file: Path,
        ssid: str,
        bssid: str,
        wordlist: str = "rockyou.txt",
        wait: bool = True,
    ) -> CrackResult | CrackJob:
        """
        Convenience method to crack a handshake.
        
        Args:
            hash_file: Path to .22000 or .cap file
            ssid: Target SSID
            bssid: Target BSSID
            wordlist: Wordlist to use
            wait: Wait for result
            
        Returns:
            Result if wait=True, Job otherwise
        """
        # Determine hash type from file
        hash_type = HashType.WPA_PMKID
        if hash_file.suffix == ".cap":
            hash_type = HashType.WPA2
        
        job = CrackJob(
            hash_type=hash_type,
            hash_file=hash_file,
            wordlist=wordlist,
            ssid=ssid,
            bssid=bssid,
        )
        
        job = await self.submit_job(job)
        
        if wait:
            return await self.wait_for_result(job.id) or CrackResult(
                job_id=job.id,
                success=False,
                error="Timeout",
            )
        
        return job
    
    # ==================== Mock Implementation ====================
    
    async def _mock_crack(self, job: CrackJob) -> None:
        """Simulate cracking process (for testing)."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        
        # Simulate progress
        for i in range(10):
            await asyncio.sleep(0.5)
            job.progress = (i + 1) * 10
            job.speed = "500 MH/s"
            job.eta = f"{10 - i}s"
        
        # Simulate result (always "mock_password" for testing)
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now()
        job.progress = 100
        
        # Create mock result
        duration = int((job.completed_at - job.started_at).total_seconds())
        
        # Deterministic "crack" based on SSID hash
        if job.ssid:
            hash_val = int(hashlib.md5(job.ssid.encode()).hexdigest()[:8], 16)
            if hash_val % 2 == 0:
                self._results[job.id] = CrackResult(
                    job_id=job.id,
                    success=True,
                    password=f"mock_{job.ssid.lower()}123",
                    duration_seconds=duration,
                    hashes_tried=1000000,
                )
                logger.info(f"[MOCK] Job {job.id} cracked!")
            else:
                self._results[job.id] = CrackResult(
                    job_id=job.id,
                    success=False,
                    duration_seconds=duration,
                    hashes_tried=1000000,
                    error="Password not in wordlist",
                )
                logger.info(f"[MOCK] Job {job.id} exhausted wordlist")
        else:
            self._results[job.id] = CrackResult(
                job_id=job.id,
                success=False,
                error="No SSID provided",
            )
    
    # ==================== Context Manager ====================
    
    async def __aenter__(self) -> HashcatCloudClient:
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


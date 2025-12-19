"""
Cloud API Routes.

REST endpoints for cloud services (Hashcat, Evilginx).
"""

from __future__ import annotations

import base64
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field

from nexus.api.auth import require_auth

logger = logging.getLogger(__name__)

cloud_router = APIRouter(prefix="/cloud", tags=["cloud"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CrackRequest(BaseModel):
    """Crack job request."""
    
    ssid: str = Field(..., description="Target SSID")
    bssid: str = Field(..., description="Target BSSID")
    hash_data: Optional[str] = Field(None, description="Base64 encoded hash file")
    wordlist: str = Field(default="rockyou.txt", description="Wordlist name")
    device_id: Optional[str] = Field(None, description="Source device")
    wait: bool = Field(default=False, description="Wait for result")


class CrackJobResponse(BaseModel):
    """Crack job response."""
    
    id: str
    status: str
    ssid: Optional[str]
    progress: float
    speed: str
    eta: str


class CrackResultResponse(BaseModel):
    """Crack result response."""
    
    job_id: str
    success: bool
    password: Optional[str]
    duration_seconds: int
    error: Optional[str]


class PhishletResponse(BaseModel):
    """Phishlet response."""
    
    name: str
    status: str
    hostname: str
    visits: int
    captures: int


class LureRequest(BaseModel):
    """Lure creation request."""
    
    phishlet: str = Field(..., description="Phishlet name")
    campaign: str = Field(default="", description="Campaign name")
    redirect_url: str = Field(default="", description="Post-capture redirect")


class LureResponse(BaseModel):
    """Lure response."""
    
    id: str
    phishlet: str
    url: str
    clicks: int
    captures: int
    campaign: str


class SessionResponse(BaseModel):
    """Session response."""
    
    id: str
    phishlet: str
    username: str
    has_cookies: bool
    ip_address: str
    captured_at: str


# =============================================================================
# Helper Functions
# =============================================================================


def get_cloud_manager(request: Request):
    """Get cloud manager from app state."""
    manager = getattr(request.app.state, "cloud_manager", None)
    if not manager:
        raise HTTPException(status_code=503, detail="Cloud manager not initialized")
    return manager


# =============================================================================
# Hashcat Endpoints
# =============================================================================


@cloud_router.get("/hashcat/status")
async def hashcat_status(request: Request, _: str = require_auth):
    """Get Hashcat cloud status."""
    cloud = get_cloud_manager(request)
    
    return {
        "available": cloud.hashcat_available,
        "mock": cloud._hashcat.is_mock if cloud._hashcat else False,
    }


@cloud_router.post("/crack", response_model=CrackJobResponse)
async def submit_crack_job(
    request: Request,
    crack: CrackRequest,
    _: str = require_auth,
):
    """Submit handshake for GPU cracking."""
    cloud = get_cloud_manager(request)
    
    if not cloud.hashcat_available:
        raise HTTPException(status_code=503, detail="Hashcat cloud not available")
    
    # Create temp file from hash data
    hash_file = None
    if crack.hash_data:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".22000", delete=False) as f:
            f.write(base64.b64decode(crack.hash_data))
            hash_file = Path(f.name)
    
    if not hash_file:
        raise HTTPException(status_code=400, detail="No hash data provided")
    
    try:
        result = await cloud.crack_handshake(
            hash_file=hash_file,
            ssid=crack.ssid,
            bssid=crack.bssid,
            wordlist=crack.wordlist,
            device_id=crack.device_id,
            wait=crack.wait,
        )
        
        if crack.wait:
            # Return result
            return CrackResultResponse(
                job_id=result.job_id,
                success=result.success,
                password=result.password,
                duration_seconds=result.duration_seconds,
                error=result.error,
            )
        else:
            # Return job
            return CrackJobResponse(
                id=result.id,
                status=result.status.value,
                ssid=result.ssid,
                progress=result.progress,
                speed=result.speed,
                eta=result.eta,
            )
            
    finally:
        # Clean up temp file
        if hash_file and hash_file.exists():
            hash_file.unlink()


@cloud_router.post("/crack/file")
async def submit_crack_file(
    request: Request,
    ssid: str = Form(...),
    bssid: str = Form(...),
    wordlist: str = Form(default="rockyou.txt"),
    file: UploadFile = File(...),
    _: str = require_auth,
):
    """Submit handshake file for cracking."""
    cloud = get_cloud_manager(request)
    
    if not cloud.hashcat_available:
        raise HTTPException(status_code=503, detail="Hashcat cloud not available")
    
    # Save uploaded file
    import tempfile
    content = await file.read()
    
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".22000", delete=False) as f:
        f.write(content)
        hash_file = Path(f.name)
    
    try:
        job = await cloud.crack_handshake(
            hash_file=hash_file,
            ssid=ssid,
            bssid=bssid,
            wordlist=wordlist,
            wait=False,
        )
        
        return {
            "id": job.id,
            "status": job.status.value,
            "ssid": ssid,
            "filename": file.filename,
        }
        
    finally:
        if hash_file.exists():
            hash_file.unlink()


@cloud_router.get("/crack/jobs", response_model=list[CrackJobResponse])
async def list_crack_jobs(
    request: Request,
    status: Optional[str] = None,
    _: str = require_auth,
):
    """List crack jobs."""
    cloud = get_cloud_manager(request)
    
    if not cloud.hashcat_available:
        return []
    
    from nexus.cloud.hashcat import JobStatus
    
    status_filter = JobStatus(status) if status else None
    jobs = await cloud.list_crack_jobs(status=status_filter)
    
    return [
        CrackJobResponse(
            id=j.id,
            status=j.status.value,
            ssid=j.ssid,
            progress=j.progress,
            speed=j.speed,
            eta=j.eta,
        )
        for j in jobs
    ]


@cloud_router.get("/crack/jobs/{job_id}", response_model=CrackJobResponse)
async def get_crack_job(
    request: Request,
    job_id: str,
    _: str = require_auth,
):
    """Get crack job status."""
    cloud = get_cloud_manager(request)
    
    job = await cloud.get_crack_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return CrackJobResponse(
        id=job.id,
        status=job.status.value,
        ssid=job.ssid,
        progress=job.progress,
        speed=job.speed,
        eta=job.eta,
    )


@cloud_router.get("/crack/jobs/{job_id}/result", response_model=CrackResultResponse)
async def get_crack_result(
    request: Request,
    job_id: str,
    _: str = require_auth,
):
    """Get crack result."""
    cloud = get_cloud_manager(request)
    
    result = await cloud.get_crack_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return CrackResultResponse(
        job_id=result.job_id,
        success=result.success,
        password=result.password,
        duration_seconds=result.duration_seconds,
        error=result.error,
    )


@cloud_router.delete("/crack/jobs/{job_id}")
async def cancel_crack_job(
    request: Request,
    job_id: str,
    _: str = require_auth,
):
    """Cancel a crack job."""
    cloud = get_cloud_manager(request)
    
    success = await cloud.cancel_crack_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already finished")
    
    return {"status": "cancelled", "job_id": job_id}


# =============================================================================
# Evilginx Endpoints
# =============================================================================


@cloud_router.get("/evilginx/status")
async def evilginx_status(request: Request, _: str = require_auth):
    """Get Evilginx VPS status."""
    cloud = get_cloud_manager(request)
    
    return {
        "available": cloud.evilginx_available,
        "mock": cloud._evilginx.is_mock if cloud._evilginx else False,
    }


@cloud_router.get("/phishlets", response_model=list[PhishletResponse])
async def list_phishlets(request: Request, _: str = require_auth):
    """List available phishlets."""
    cloud = get_cloud_manager(request)
    
    phishlets = await cloud.list_phishlets()
    
    return [
        PhishletResponse(
            name=p.name,
            status=p.status.value,
            hostname=p.hostname,
            visits=p.visits,
            captures=p.captures,
        )
        for p in phishlets
    ]


@cloud_router.post("/phishlets/{name}/enable", response_model=PhishletResponse)
async def enable_phishlet(
    request: Request,
    name: str,
    hostname: Optional[str] = None,
    _: str = require_auth,
):
    """Enable a phishlet."""
    cloud = get_cloud_manager(request)
    
    phishlet = await cloud.enable_phishlet(name, hostname)
    if not phishlet:
        raise HTTPException(status_code=404, detail="Phishlet not found or enable failed")
    
    return PhishletResponse(
        name=phishlet.name,
        status=phishlet.status.value,
        hostname=phishlet.hostname,
        visits=phishlet.visits,
        captures=phishlet.captures,
    )


@cloud_router.post("/phishlets/{name}/disable")
async def disable_phishlet(
    request: Request,
    name: str,
    _: str = require_auth,
):
    """Disable a phishlet."""
    cloud = get_cloud_manager(request)
    
    success = await cloud.disable_phishlet(name)
    if not success:
        raise HTTPException(status_code=404, detail="Phishlet not found")
    
    return {"status": "disabled", "phishlet": name}


@cloud_router.post("/lures", response_model=LureResponse)
async def create_lure(
    request: Request,
    lure: LureRequest,
    _: str = require_auth,
):
    """Create a phishing lure."""
    cloud = get_cloud_manager(request)
    
    result = await cloud.create_phishing_lure(
        phishlet=lure.phishlet,
        campaign=lure.campaign,
        redirect_url=lure.redirect_url,
    )
    
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create lure")
    
    return LureResponse(
        id=result.id,
        phishlet=result.phishlet,
        url=result.url,
        clicks=result.clicks,
        captures=result.captures,
        campaign=result.campaign,
    )


@cloud_router.get("/lures", response_model=list[LureResponse])
async def list_lures(
    request: Request,
    phishlet: Optional[str] = None,
    _: str = require_auth,
):
    """List phishing lures."""
    cloud = get_cloud_manager(request)
    
    lures = await cloud.list_lures(phishlet)
    
    return [
        LureResponse(
            id=l.id,
            phishlet=l.phishlet,
            url=l.url,
            clicks=l.clicks,
            captures=l.captures,
            campaign=l.campaign,
        )
        for l in lures
    ]


@cloud_router.delete("/lures/{lure_id}")
async def delete_lure(
    request: Request,
    lure_id: str,
    _: str = require_auth,
):
    """Delete a lure."""
    cloud = get_cloud_manager(request)
    
    success = await cloud.delete_lure(lure_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lure not found")
    
    return {"status": "deleted", "lure_id": lure_id}


@cloud_router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    phishlet: Optional[str] = None,
    _: str = require_auth,
):
    """List captured phishing sessions."""
    cloud = get_cloud_manager(request)
    
    sessions = await cloud.get_phishing_sessions(phishlet)
    
    return [
        SessionResponse(
            id=s.id,
            phishlet=s.phishlet,
            username=s.username,
            has_cookies=len(s.cookies) > 0,
            ip_address=s.ip_address,
            captured_at=s.captured_at.isoformat(),
        )
        for s in sessions
    ]


@cloud_router.get("/sessions/{session_id}")
async def get_session(
    request: Request,
    session_id: str,
    _: str = require_auth,
):
    """Get session details including cookies."""
    cloud = get_cloud_manager(request)
    
    if not cloud._evilginx:
        raise HTTPException(status_code=503, detail="Evilginx not available")
    
    session = await cloud._evilginx.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "id": session.id,
        "phishlet": session.phishlet,
        "username": session.username,
        "password": session.password,  # Full details
        "cookies": session.cookies,
        "tokens": session.tokens,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "captured_at": session.captured_at.isoformat(),
    }


@cloud_router.get("/sessions/{session_id}/cookies")
async def get_session_cookies(
    request: Request,
    session_id: str,
    _: str = require_auth,
):
    """Get session cookies for browser import."""
    cloud = get_cloud_manager(request)
    
    cookies = await cloud.get_session_cookies(session_id)
    if not cookies:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"cookies": cookies}


# =============================================================================
# Stats Endpoint
# =============================================================================


@cloud_router.get("/stats")
async def get_cloud_stats(request: Request, _: str = require_auth):
    """Get cloud services statistics."""
    cloud = get_cloud_manager(request)
    
    return await cloud.get_stats()


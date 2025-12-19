"""
Sync API Routes.

Endpoints for synchronizing data from field devices (MoMo, GhostBridge, Mimic).
Handles handshakes, credentials, loot, and status updates.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field

from nexus.api.auth import require_auth

logger = logging.getLogger(__name__)

sync_router = APIRouter(prefix="/sync", tags=["sync"])


# =============================================================================
# Request/Response Models
# =============================================================================


class HandshakeUpload(BaseModel):
    """Handshake upload request."""
    
    device_id: str = Field(..., description="Source device ID")
    ssid: str = Field(..., description="Target SSID")
    bssid: str = Field(..., description="Target BSSID")
    channel: int = Field(..., description="WiFi channel")
    capture_type: str = Field(default="4way", description="4way, pmkid, wpa3")
    timestamp: Optional[str] = Field(None, description="Capture timestamp ISO8601")
    
    # Base64 encoded capture data
    data: Optional[str] = Field(None, description="Base64 encoded capture file")
    
    # Optional metadata
    signal_strength: Optional[int] = Field(None, description="Signal dBm")
    client_mac: Optional[str] = Field(None, description="Client MAC for 4way")
    gps: Optional[list[float]] = Field(None, description="[lat, lon]")


class HandshakeResponse(BaseModel):
    """Handshake upload response."""
    
    id: str
    status: str  # received, queued, cracking, cracked, failed
    device_id: str
    ssid: str
    bssid: str
    capture_type: str
    job_id: Optional[str] = None  # Cloud cracking job ID


class CredentialUpload(BaseModel):
    """Credential upload from Evil Twin / Captive Portal."""
    
    device_id: str = Field(..., description="Source device ID")
    ssid: str = Field(..., description="Target/fake SSID")
    capture_type: str = Field(default="captive", description="captive, eap, wpa_enterprise")
    
    # Credential data
    username: Optional[str] = Field(None)
    password: Optional[str] = Field(None)
    domain: Optional[str] = Field(None)
    
    # Client info
    client_mac: str = Field(...)
    client_ip: Optional[str] = Field(None)
    user_agent: Optional[str] = Field(None)
    
    timestamp: Optional[str] = Field(None)
    gps: Optional[list[float]] = Field(None)


class CrackResultUpload(BaseModel):
    """Crack result upload."""
    
    device_id: str = Field(..., description="Source device ID")
    handshake_id: str = Field(..., description="Original handshake ID")
    
    success: bool = Field(...)
    password: Optional[str] = Field(None)
    duration_seconds: Optional[int] = Field(None)
    method: str = Field(default="john", description="john, hashcat, cloud")
    wordlist: Optional[str] = Field(None)


class LootUpload(BaseModel):
    """Generic loot/data upload."""
    
    device_id: str = Field(..., description="Source device ID")
    loot_type: str = Field(..., description="Type: file, text, binary")
    name: str = Field(..., description="Loot name/filename")
    
    # Content (mutually exclusive)
    text: Optional[str] = Field(None, description="Text content")
    data: Optional[str] = Field(None, description="Base64 encoded binary")
    
    # Metadata
    source: Optional[str] = Field(None, description="Where this came from")
    tags: list[str] = Field(default_factory=list)
    gps: Optional[list[float]] = Field(None)


class DeviceStatusUpdate(BaseModel):
    """Device status update."""
    
    device_id: str = Field(...)
    
    # System stats
    battery: Optional[int] = Field(None, ge=0, le=100)
    temperature: Optional[int] = Field(None)
    uptime: Optional[int] = Field(None)
    disk_free: Optional[int] = Field(None)
    memory_free: Optional[int] = Field(None)
    
    # WiFi stats
    aps_seen: Optional[int] = Field(None)
    handshakes_captured: Optional[int] = Field(None)
    clients_seen: Optional[int] = Field(None)
    
    # Location
    gps: Optional[list[float]] = Field(None)
    
    # Current activity
    mode: Optional[str] = Field(None, description="passive, active, eviltwin")
    current_target: Optional[str] = Field(None)


class GhostBeacon(BaseModel):
    """GhostBridge beacon."""
    
    device_id: str = Field(...)
    tunnel_status: str = Field(default="unknown", description="up, down, unknown")
    
    # Network info
    internal_ip: Optional[str] = Field(None)
    external_ip: Optional[str] = Field(None)
    gateway_mac: Optional[str] = Field(None)
    
    # Stats
    bytes_in: Optional[int] = Field(None)
    bytes_out: Optional[int] = Field(None)
    uptime: Optional[int] = Field(None)


class MimicTrigger(BaseModel):
    """Mimic trigger event."""
    
    device_id: str = Field(...)
    trigger_type: str = Field(..., description="usb_insert, button, scheduled, remote")
    
    # Payload info
    payload_name: Optional[str] = Field(None)
    target_os: Optional[str] = Field(None)
    
    # Result
    success: bool = Field(...)
    execution_time_ms: Optional[int] = Field(None)
    output: Optional[str] = Field(None)


# =============================================================================
# Storage Helper
# =============================================================================


class SyncStorage:
    """Simple file-based storage for synced data."""
    
    def __init__(self, base_path: str = "./sync_data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirs
        (self.base_path / "handshakes").mkdir(exist_ok=True)
        (self.base_path / "credentials").mkdir(exist_ok=True)
        (self.base_path / "loot").mkdir(exist_ok=True)
        (self.base_path / "status").mkdir(exist_ok=True)
    
    def generate_id(self, prefix: str, data: str) -> str:
        """Generate unique ID."""
        hash_input = f"{prefix}:{data}:{datetime.now().isoformat()}"
        return f"{prefix}_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"
    
    async def save_handshake(self, hs: HandshakeUpload) -> str:
        """Save handshake data."""
        import json
        
        hs_id = self.generate_id("hs", f"{hs.bssid}:{hs.ssid}")
        hs_dir = self.base_path / "handshakes" / hs_id
        hs_dir.mkdir(exist_ok=True)
        
        # Save metadata
        meta = {
            "id": hs_id,
            "device_id": hs.device_id,
            "ssid": hs.ssid,
            "bssid": hs.bssid,
            "channel": hs.channel,
            "capture_type": hs.capture_type,
            "timestamp": hs.timestamp or datetime.now().isoformat(),
            "signal_strength": hs.signal_strength,
            "client_mac": hs.client_mac,
            "gps": hs.gps,
            "status": "received",
        }
        
        with open(hs_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)
        
        # Save capture file if provided
        if hs.data:
            ext = ".22000" if hs.capture_type == "pmkid" else ".cap"
            with open(hs_dir / f"capture{ext}", "wb") as f:
                f.write(base64.b64decode(hs.data))
        
        logger.info(f"Saved handshake {hs_id} from {hs.device_id}")
        return hs_id
    
    async def save_credential(self, cred: CredentialUpload) -> str:
        """Save captured credential."""
        import json
        
        cred_id = self.generate_id("cred", f"{cred.client_mac}:{cred.ssid}")
        cred_file = self.base_path / "credentials" / f"{cred_id}.json"
        
        data = {
            "id": cred_id,
            "device_id": cred.device_id,
            "ssid": cred.ssid,
            "capture_type": cred.capture_type,
            "username": cred.username,
            "password": cred.password,
            "domain": cred.domain,
            "client_mac": cred.client_mac,
            "client_ip": cred.client_ip,
            "user_agent": cred.user_agent,
            "timestamp": cred.timestamp or datetime.now().isoformat(),
            "gps": cred.gps,
        }
        
        with open(cred_file, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved credential {cred_id} from {cred.device_id}")
        return cred_id
    
    async def save_loot(self, loot: LootUpload) -> str:
        """Save generic loot."""
        import json
        
        loot_id = self.generate_id("loot", f"{loot.device_id}:{loot.name}")
        loot_dir = self.base_path / "loot" / loot_id
        loot_dir.mkdir(exist_ok=True)
        
        # Save metadata
        meta = {
            "id": loot_id,
            "device_id": loot.device_id,
            "loot_type": loot.loot_type,
            "name": loot.name,
            "source": loot.source,
            "tags": loot.tags,
            "gps": loot.gps,
            "timestamp": datetime.now().isoformat(),
        }
        
        with open(loot_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)
        
        # Save content
        if loot.text:
            with open(loot_dir / loot.name, "w") as f:
                f.write(loot.text)
        elif loot.data:
            with open(loot_dir / loot.name, "wb") as f:
                f.write(base64.b64decode(loot.data))
        
        logger.info(f"Saved loot {loot_id} from {loot.device_id}")
        return loot_id
    
    async def update_status(self, status: DeviceStatusUpdate) -> None:
        """Update device status."""
        import json
        
        status_file = self.base_path / "status" / f"{status.device_id}.json"
        
        data = {
            "device_id": status.device_id,
            "last_update": datetime.now().isoformat(),
            "battery": status.battery,
            "temperature": status.temperature,
            "uptime": status.uptime,
            "disk_free": status.disk_free,
            "memory_free": status.memory_free,
            "aps_seen": status.aps_seen,
            "handshakes_captured": status.handshakes_captured,
            "clients_seen": status.clients_seen,
            "gps": status.gps,
            "mode": status.mode,
            "current_target": status.current_target,
        }
        
        with open(status_file, "w") as f:
            json.dump(data, f, indent=2)


# Global storage instance
_storage: SyncStorage | None = None


def get_storage() -> SyncStorage:
    """Get or create storage instance."""
    global _storage
    if _storage is None:
        _storage = SyncStorage()
    return _storage


# =============================================================================
# Handshake Endpoints
# =============================================================================


@sync_router.post("/handshake", response_model=HandshakeResponse)
async def upload_handshake(
    request: Request,
    handshake: HandshakeUpload,
    _: str = require_auth,
):
    """
    Upload captured handshake from MoMo.
    
    Supports 4-way handshake, PMKID, and WPA3 captures.
    Optionally queues for cloud cracking.
    """
    storage = get_storage()
    hs_id = await storage.save_handshake(handshake)
    
    # TODO: Queue for cloud cracking if enabled
    job_id = None
    
    # Notify via Swarm if available
    swarm = getattr(request.app.state, "swarm_manager", None)
    if swarm:
        from nexus.swarm.protocol import EventCode
        await swarm.broadcast_alert(EventCode.HANDSHAKE_CAPTURED, {
            "id": hs_id,
            "ssid": handshake.ssid,
            "bssid": handshake.bssid,
            "device": handshake.device_id,
        })
    
    return HandshakeResponse(
        id=hs_id,
        status="received",
        device_id=handshake.device_id,
        ssid=handshake.ssid,
        bssid=handshake.bssid,
        capture_type=handshake.capture_type,
        job_id=job_id,
    )


@sync_router.post("/handshake/file")
async def upload_handshake_file(
    request: Request,
    device_id: str = Form(...),
    ssid: str = Form(...),
    bssid: str = Form(...),
    channel: int = Form(...),
    capture_type: str = Form(default="4way"),
    file: UploadFile = File(...),
    _: str = require_auth,
):
    """Upload handshake as multipart file."""
    storage = get_storage()
    
    # Read file content
    content = await file.read()
    data_b64 = base64.b64encode(content).decode()
    
    handshake = HandshakeUpload(
        device_id=device_id,
        ssid=ssid,
        bssid=bssid,
        channel=channel,
        capture_type=capture_type,
        data=data_b64,
    )
    
    hs_id = await storage.save_handshake(handshake)
    
    return {
        "id": hs_id,
        "status": "received",
        "filename": file.filename,
        "size": len(content),
    }


@sync_router.get("/handshakes")
async def list_handshakes(
    request: Request,
    device_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    _: str = require_auth,
):
    """List synced handshakes."""
    import json
    
    storage = get_storage()
    hs_dir = storage.base_path / "handshakes"
    
    results = []
    for item in hs_dir.iterdir():
        if item.is_dir():
            meta_file = item / "meta.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    meta = json.load(f)
                
                # Apply filters
                if device_id and meta.get("device_id") != device_id:
                    continue
                if status and meta.get("status") != status:
                    continue
                
                results.append(meta)
                
                if len(results) >= limit:
                    break
    
    return results


# =============================================================================
# Credential Endpoints
# =============================================================================


@sync_router.post("/credential")
async def upload_credential(
    request: Request,
    credential: CredentialUpload,
    _: str = require_auth,
):
    """Upload captured credential from Evil Twin / Captive Portal."""
    storage = get_storage()
    cred_id = await storage.save_credential(credential)
    
    # Notify via Swarm
    swarm = getattr(request.app.state, "swarm_manager", None)
    if swarm:
        from nexus.swarm.protocol import EventCode
        await swarm.broadcast_alert(EventCode.EVIL_TWIN_CREDENTIAL, {
            "id": cred_id,
            "ssid": credential.ssid,
            "username": credential.username,
            "device": credential.device_id,
        })
    
    return {
        "id": cred_id,
        "status": "received",
        "device_id": credential.device_id,
    }


@sync_router.get("/credentials")
async def list_credentials(
    request: Request,
    device_id: Optional[str] = None,
    limit: int = 100,
    _: str = require_auth,
):
    """List captured credentials."""
    import json
    
    storage = get_storage()
    cred_dir = storage.base_path / "credentials"
    
    results = []
    for item in cred_dir.glob("*.json"):
        with open(item) as f:
            cred = json.load(f)
        
        if device_id and cred.get("device_id") != device_id:
            continue
        
        # Mask password for listing
        if cred.get("password"):
            cred["password"] = "***"
        
        results.append(cred)
        
        if len(results) >= limit:
            break
    
    return results


# =============================================================================
# Crack Result Endpoints
# =============================================================================


@sync_router.post("/crack-result")
async def upload_crack_result(
    request: Request,
    result: CrackResultUpload,
    _: str = require_auth,
):
    """Upload crack result (from local John or cloud Hashcat)."""
    import json
    
    storage = get_storage()
    
    # Update handshake status
    hs_dir = storage.base_path / "handshakes" / result.handshake_id
    if hs_dir.exists():
        meta_file = hs_dir / "meta.json"
        with open(meta_file) as f:
            meta = json.load(f)
        
        meta["status"] = "cracked" if result.success else "failed"
        meta["password"] = result.password
        meta["crack_duration"] = result.duration_seconds
        meta["crack_method"] = result.method
        meta["crack_wordlist"] = result.wordlist
        meta["cracked_at"] = datetime.now().isoformat()
        
        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=2)
        
        # Notify via Swarm
        if result.success:
            swarm = getattr(request.app.state, "swarm_manager", None)
            if swarm:
                from nexus.swarm.protocol import EventCode
                await swarm.broadcast_alert(EventCode.PASSWORD_CRACKED, {
                    "handshake_id": result.handshake_id,
                    "ssid": meta.get("ssid"),
                    "password": result.password,
                    "method": result.method,
                })
        
        return {
            "status": "updated",
            "handshake_id": result.handshake_id,
            "cracked": result.success,
        }
    
    raise HTTPException(status_code=404, detail="Handshake not found")


# =============================================================================
# Loot Endpoints
# =============================================================================


@sync_router.post("/loot")
async def upload_loot(
    request: Request,
    loot: LootUpload,
    _: str = require_auth,
):
    """Upload generic loot/data."""
    storage = get_storage()
    loot_id = await storage.save_loot(loot)
    
    return {
        "id": loot_id,
        "status": "received",
        "device_id": loot.device_id,
        "name": loot.name,
    }


@sync_router.get("/loot")
async def list_loot(
    request: Request,
    device_id: Optional[str] = None,
    loot_type: Optional[str] = None,
    limit: int = 100,
    _: str = require_auth,
):
    """List synced loot."""
    import json
    
    storage = get_storage()
    loot_dir = storage.base_path / "loot"
    
    results = []
    for item in loot_dir.iterdir():
        if item.is_dir():
            meta_file = item / "meta.json"
            if meta_file.exists():
                with open(meta_file) as f:
                    meta = json.load(f)
                
                if device_id and meta.get("device_id") != device_id:
                    continue
                if loot_type and meta.get("loot_type") != loot_type:
                    continue
                
                results.append(meta)
                
                if len(results) >= limit:
                    break
    
    return results


# =============================================================================
# Status Endpoints
# =============================================================================


@sync_router.post("/status")
async def update_device_status(
    request: Request,
    status: DeviceStatusUpdate,
    _: str = require_auth,
):
    """Update device status (heartbeat)."""
    storage = get_storage()
    await storage.update_status(status)
    
    # Update fleet registry if available
    fleet = getattr(request.app.state, "fleet_manager", None)
    if fleet:
        try:
            await fleet.registry.update(status.device_id, {
                "battery": status.battery,
                "temperature": status.temperature,
                "location": {"lat": status.gps[0], "lon": status.gps[1]} if status.gps else None,
            })
        except Exception as e:
            logger.warning(f"Failed to update fleet registry: {e}")
    
    return {"status": "ok", "device_id": status.device_id}


@sync_router.get("/status/{device_id}")
async def get_device_status(
    request: Request,
    device_id: str,
    _: str = require_auth,
):
    """Get last known device status."""
    import json
    
    storage = get_storage()
    status_file = storage.base_path / "status" / f"{device_id}.json"
    
    if not status_file.exists():
        raise HTTPException(status_code=404, detail="Device status not found")
    
    with open(status_file) as f:
        return json.load(f)


# =============================================================================
# GhostBridge Endpoints
# =============================================================================


@sync_router.post("/ghost/beacon")
async def ghost_beacon(
    request: Request,
    beacon: GhostBeacon,
    _: str = require_auth,
):
    """Receive GhostBridge beacon."""
    import json
    
    storage = get_storage()
    beacon_file = storage.base_path / "status" / f"ghost_{beacon.device_id}.json"
    
    data = {
        "device_id": beacon.device_id,
        "type": "ghostbridge",
        "last_beacon": datetime.now().isoformat(),
        "tunnel_status": beacon.tunnel_status,
        "internal_ip": beacon.internal_ip,
        "external_ip": beacon.external_ip,
        "gateway_mac": beacon.gateway_mac,
        "bytes_in": beacon.bytes_in,
        "bytes_out": beacon.bytes_out,
        "uptime": beacon.uptime,
    }
    
    with open(beacon_file, "w") as f:
        json.dump(data, f, indent=2)
    
    # Notify via Swarm
    swarm = getattr(request.app.state, "swarm_manager", None)
    if swarm:
        from nexus.swarm.protocol import EventCode
        await swarm.broadcast_alert(EventCode.GHOST_BEACON, {
            "device": beacon.device_id,
            "tunnel": beacon.tunnel_status,
            "ip": beacon.internal_ip,
        })
    
    return {"status": "ok", "device_id": beacon.device_id}


# =============================================================================
# Mimic Endpoints
# =============================================================================


@sync_router.post("/mimic/trigger")
async def mimic_trigger(
    request: Request,
    trigger: MimicTrigger,
    _: str = require_auth,
):
    """Record Mimic trigger event."""
    import json
    
    storage = get_storage()
    
    # Save to loot
    loot_id = await storage.save_loot(LootUpload(
        device_id=trigger.device_id,
        loot_type="text",
        name=f"mimic_trigger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        text=json.dumps({
            "trigger_type": trigger.trigger_type,
            "payload_name": trigger.payload_name,
            "target_os": trigger.target_os,
            "success": trigger.success,
            "execution_time_ms": trigger.execution_time_ms,
            "output": trigger.output,
            "timestamp": datetime.now().isoformat(),
        }),
        source="mimic",
        tags=["mimic", "trigger", trigger.trigger_type],
    ))
    
    # Notify via Swarm
    swarm = getattr(request.app.state, "swarm_manager", None)
    if swarm:
        from nexus.swarm.protocol import EventCode
        await swarm.broadcast_alert(EventCode.MIMIC_TRIGGER, {
            "device": trigger.device_id,
            "trigger": trigger.trigger_type,
            "payload": trigger.payload_name,
            "success": trigger.success,
        })
    
    return {
        "status": "ok",
        "device_id": trigger.device_id,
        "loot_id": loot_id,
    }


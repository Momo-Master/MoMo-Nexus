"""
Cloud Integration for Nexus.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Interfaces for cloud services:
- GPU Hashcat cracking (VPS or cloud provider)
- Evilginx AiTM proxy control (dedicated VPS)
- Data sync and backup

:copyright: (c) 2025 MoMo Team
:license: MIT
"""

from nexus.cloud.evilginx import EvilginxClient, Lure, Phishlet, PhishletStatus, Session
from nexus.cloud.hashcat import CrackJob, CrackResult, HashcatCloudClient, HashType, JobStatus
from nexus.cloud.manager import CloudManager

__all__ = [
    # Hashcat
    "HashcatCloudClient",
    "CrackJob",
    "CrackResult",
    "HashType",
    "JobStatus",
    # Evilginx
    "EvilginxClient",
    "Phishlet",
    "PhishletStatus",
    "Lure",
    "Session",
    # Manager
    "CloudManager",
]


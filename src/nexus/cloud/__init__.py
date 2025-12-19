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

from nexus.cloud.hashcat import HashcatCloudClient, CrackJob, CrackResult
from nexus.cloud.evilginx import EvilginxClient, Phishlet, Session
from nexus.cloud.manager import CloudManager

__all__ = [
    # Hashcat
    "HashcatCloudClient",
    "CrackJob",
    "CrackResult",
    # Evilginx
    "EvilginxClient",
    "Phishlet",
    "Session",
    # Manager
    "CloudManager",
]


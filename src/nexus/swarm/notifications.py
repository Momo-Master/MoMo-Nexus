"""
Operator Notifications
~~~~~~~~~~~~~~~~~~~~~~

Human-readable notification templates for LoRa/Meshtastic.
Optimized for phone display in Meshtastic app.

Max message size: ~200 bytes (LoRa limit)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class NotifyIcon(str, Enum):
    """Emoji icons for notifications."""
    # Status
    OK = "✅"
    WARN = "⚠️"
    ERROR = "❌"
    INFO = "ℹ️"
    
    # Events
    HANDSHAKE = "🤝"
    CRACK = "🔓"
    WIFI = "📶"
    TARGET = "🎯"
    ALERT = "🚨"
    GPS = "📍"
    BATTERY = "🔋"
    TEMP = "🌡️"
    
    # Devices
    MOMO = "📡"
    GHOST = "👻"
    MIMIC = "🎭"
    NEXUS = "🌐"


@dataclass
class OperatorNotification:
    """
    Operator notification message.
    
    Designed for quick reading on phone screen.
    """
    icon: NotifyIcon
    title: str
    body: str
    priority: int = 1  # 1=low, 2=normal, 3=high, 4=critical
    
    def to_text(self, compact: bool = True) -> str:
        """
        Format as plain text for LoRa transmission.
        
        Args:
            compact: Use compact format (recommended)
            
        Returns:
            Formatted string, max ~200 chars
        """
        if compact:
            # Ultra-compact: "🤝 Handshake | CORP-WiFi captured"
            return f"{self.icon.value} {self.title} | {self.body}"
        else:
            # Multi-line: 
            # "🤝 Handshake
            #  CORP-WiFi captured
            #  14:32"
            time_str = datetime.now().strftime("%H:%M")
            return f"{self.icon.value} {self.title}\n{self.body}\n{time_str}"
    
    def __str__(self) -> str:
        return self.to_text(compact=True)


class NotificationBuilder:
    """
    Builder for operator notifications.
    
    Provides pre-formatted templates for common events.
    
    Example:
        >>> builder = NotificationBuilder()
        >>> msg = builder.handshake_captured("CORP-WiFi", "AA:BB:CC:DD:EE:FF")
        >>> print(msg)
        🤝 Handshake | CORP-WiFi yakalandı
    """
    
    # ==================== WiFi Events ====================
    
    def handshake_captured(self, ssid: str, bssid: str = "") -> OperatorNotification:
        """Handshake yakalandı bildirimi."""
        body = f"{ssid[:20]} yakalandı"
        if bssid:
            body += f" ({bssid[-8:]})"
        return OperatorNotification(
            icon=NotifyIcon.HANDSHAKE,
            title="Handshake",
            body=body,
            priority=3
        )
    
    def pmkid_captured(self, ssid: str) -> OperatorNotification:
        """PMKID yakalandı bildirimi."""
        return OperatorNotification(
            icon=NotifyIcon.HANDSHAKE,
            title="PMKID",
            body=f"{ssid[:20]} yakalandı",
            priority=3
        )
    
    def password_cracked(self, ssid: str, password: str) -> OperatorNotification:
        """Şifre kırıldı bildirimi."""
        # Şifreyi kısalt (güvenlik)
        masked = password[:3] + "***" if len(password) > 3 else "***"
        return OperatorNotification(
            icon=NotifyIcon.CRACK,
            title="Kırıldı!",
            body=f"{ssid[:15]}: {masked}",
            priority=4
        )
    
    def new_target(self, ssid: str, security: str = "WPA2") -> OperatorNotification:
        """Yeni hedef tespit edildi."""
        return OperatorNotification(
            icon=NotifyIcon.TARGET,
            title="Hedef",
            body=f"{ssid[:20]} ({security})",
            priority=2
        )
    
    # ==================== Attack Events ====================
    
    def evil_twin_connect(self, client_mac: str, ssid: str) -> OperatorNotification:
        """Evil Twin'e bağlantı."""
        return OperatorNotification(
            icon=NotifyIcon.WIFI,
            title="ET Bağlantı",
            body=f"{client_mac[-8:]} → {ssid[:12]}",
            priority=3
        )
    
    def credential_captured(
        self, 
        cred_type: str, 
        username: str = "", 
        target: str = ""
    ) -> OperatorNotification:
        """Credential yakalandı."""
        body = cred_type
        if username:
            body += f": {username[:15]}"
        if target:
            body += f" @{target[:10]}"
        return OperatorNotification(
            icon=NotifyIcon.CRACK,
            title="Credential",
            body=body,
            priority=4
        )
    
    def karma_client(self, client_mac: str, probed_ssid: str) -> OperatorNotification:
        """Karma/MANA client yakalandı."""
        return OperatorNotification(
            icon=NotifyIcon.WIFI,
            title="Karma",
            body=f"{client_mac[-8:]} arıyor: {probed_ssid[:12]}",
            priority=2
        )
    
    # ==================== Device Events ====================
    
    def ghost_beacon(self, device_id: str, status: str = "online") -> OperatorNotification:
        """GhostBridge beacon."""
        return OperatorNotification(
            icon=NotifyIcon.GHOST,
            title="Ghost",
            body=f"{device_id}: {status}",
            priority=2
        )
    
    def mimic_trigger(self, payload: str, target_os: str = "") -> OperatorNotification:
        """Mimic tetiklendi."""
        body = payload[:20]
        if target_os:
            body += f" ({target_os})"
        return OperatorNotification(
            icon=NotifyIcon.MIMIC,
            title="Mimic",
            body=body,
            priority=3
        )
    
    def device_online(self, device_id: str, device_type: str = "momo") -> OperatorNotification:
        """Cihaz çevrimiçi."""
        icons = {
            "momo": NotifyIcon.MOMO,
            "ghost": NotifyIcon.GHOST,
            "mimic": NotifyIcon.MIMIC,
            "nexus": NotifyIcon.NEXUS,
        }
        return OperatorNotification(
            icon=icons.get(device_type, NotifyIcon.INFO),
            title="Online",
            body=device_id,
            priority=1
        )
    
    def device_offline(self, device_id: str) -> OperatorNotification:
        """Cihaz çevrimdışı."""
        return OperatorNotification(
            icon=NotifyIcon.WARN,
            title="Offline",
            body=device_id,
            priority=2
        )
    
    # ==================== System Events ====================
    
    def low_battery(self, device_id: str, percent: int) -> OperatorNotification:
        """Düşük batarya uyarısı."""
        return OperatorNotification(
            icon=NotifyIcon.BATTERY,
            title="Batarya",
            body=f"{device_id}: %{percent}",
            priority=3 if percent < 20 else 2
        )
    
    def high_temp(self, device_id: str, temp: int) -> OperatorNotification:
        """Yüksek sıcaklık uyarısı."""
        return OperatorNotification(
            icon=NotifyIcon.TEMP,
            title="Sıcaklık",
            body=f"{device_id}: {temp}°C",
            priority=3
        )
    
    def alert(self, message: str) -> OperatorNotification:
        """Genel uyarı."""
        return OperatorNotification(
            icon=NotifyIcon.ALERT,
            title="Uyarı",
            body=message[:50],
            priority=4
        )
    
    # ==================== Status Summary ====================
    
    def status_summary(
        self,
        devices: int,
        handshakes: int,
        cracked: int,
        alerts: int = 0
    ) -> OperatorNotification:
        """
        Durum özeti.
        
        Format: "📊 Durum | D:3 H:12 C:5 A:2"
        """
        body = f"D:{devices} H:{handshakes} C:{cracked}"
        if alerts > 0:
            body += f" A:{alerts}"
        return OperatorNotification(
            icon=NotifyIcon.INFO,
            title="Durum",
            body=body,
            priority=1
        )
    
    def full_status(
        self,
        devices: int,
        handshakes: int,
        cracked: int,
        uptime_hours: int,
        alerts: int = 0
    ) -> str:
        """
        Tam durum raporu (multi-line).
        
        Format:
        ┌─ MoMo Durum ─┐
        │ 📡 3 cihaz   │
        │ 🤝 12 hs     │
        │ 🔓 5 crack   │
        │ ⏱️ 4h uptime │
        └──────────────┘
        """
        lines = [
            "┌─ MoMo ─┐",
            f"│📡 {devices} cihaz",
            f"│🤝 {handshakes} hs",
            f"│🔓 {cracked} crack",
            f"│⏱️ {uptime_hours}h up",
        ]
        if alerts > 0:
            lines.append(f"│🚨 {alerts} alert")
        lines.append("└────────┘")
        return "\n".join(lines)
    
    def compact_status(
        self,
        devices: int,
        handshakes: int,
        cracked: int
    ) -> str:
        """
        Ultra-compact status (1 line).
        
        Format: "📡3 🤝12 🔓5"
        """
        return f"📡{devices} 🤝{handshakes} 🔓{cracked}"


# Singleton instance
notifications = NotificationBuilder()


# ==================== Quick Access Functions ====================

def notify_handshake(ssid: str, bssid: str = "") -> str:
    """Quick: Handshake notification."""
    return str(notifications.handshake_captured(ssid, bssid))


def notify_cracked(ssid: str, password: str) -> str:
    """Quick: Password cracked notification."""
    return str(notifications.password_cracked(ssid, password))


def notify_status(devices: int, handshakes: int, cracked: int) -> str:
    """Quick: Status summary."""
    return str(notifications.status_summary(devices, handshakes, cracked))


def notify_alert(message: str) -> str:
    """Quick: Alert notification."""
    return str(notifications.alert(message))


// ═══════════════════════════════════════════════════════════════════════════
// NEXUS DASHBOARD - TYPE DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════

export type DeviceType = 'momo' | 'ghostbridge' | 'mimic' | 'nexus';
export type DeviceStatus = 'online' | 'offline' | 'degraded';
export type ChannelType = 'wifi' | 'lora' | 'cellular' | 'ble';
export type CrackStatus = 'pending' | 'cracking' | 'cracked' | 'failed';
export type AlertLevel = 'info' | 'warning' | 'error' | 'critical';

export interface Device {
  id: string;
  name: string;
  type: DeviceType;
  status: DeviceStatus;
  lastSeen: string;
  battery?: number;
  temperature?: number;
  location?: {
    lat: number;
    lon: number;
  };
  stats: {
    captures: number;
    uptime: number;
  };
  channel: ChannelType;
}

export interface Handshake {
  id: string;
  ssid: string;
  bssid: string;
  capturedAt: string;
  capturedBy: string;
  status: CrackStatus;
  password?: string;
  security: 'WPA2' | 'WPA3' | 'WPA' | 'WEP';
  signal?: number;
}

export interface CrackJob {
  id: string;
  handshakeId: string;
  ssid: string;
  status: CrackStatus;
  progress: number;
  startedAt: string;
  completedAt?: string;
  password?: string;
  hashRate?: number;
  wordlist: string;
}

export interface Alert {
  id: string;
  level: AlertLevel;
  message: string;
  source: string;
  timestamp: string;
  read: boolean;
}

export interface Activity {
  id: string;
  type: 'handshake' | 'crack' | 'device' | 'alert' | 'credential';
  icon: string;
  message: string;
  timestamp: string;
  color: 'green' | 'cyan' | 'magenta' | 'orange' | 'red';
}

export interface Stats {
  devicesOnline: number;
  devicesTotal: number;
  handshakesTotal: number;
  handshakesToday: number;
  crackedTotal: number;
  crackedToday: number;
  alertsActive: number;
}

export interface ChannelStatus {
  type: ChannelType;
  status: 'up' | 'degraded' | 'down';
  latency: number;
  lastCheck: string;
}


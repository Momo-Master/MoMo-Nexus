import { useState } from 'react';
import {
  Wifi,
  Radio,
  Signal,
  Bluetooth,
  Cloud,
  Shield,
  Bell,
  Database,
  Save,
  RefreshCw,
  Eye,
  EyeOff,
  Server,
  Key,
  User,
  Clock,
  HardDrive,
  Trash2,
  Download,
  Keyboard,
  Palette,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { ThemeToggle } from '../components/ui/ThemeToggle';
import { Modal } from '../components/ui/Modal';
import { KeyboardShortcutsList } from '../hooks/useKeyboardShortcuts';
import { exportDevices, exportHandshakes, exportCrackJobs, exportSessions } from '../lib/export';
import { nexusToast } from '../components/ui/Toast';

interface ChannelConfig {
  id: string;
  name: string;
  enabled: boolean;
  priority: number;
  config: Record<string, string>;
}

interface CloudEndpoint {
  id: string;
  name: string;
  url: string;
  apiKey: string;
  status: 'connected' | 'error' | 'unknown';
}

// Mock data
const mockChannels: ChannelConfig[] = [
  {
    id: 'wifi',
    name: 'WiFi',
    enabled: true,
    priority: 1,
    config: { ssid: 'NEXUS-AP', password: '••••••••' },
  },
  {
    id: 'lora',
    name: 'LoRa',
    enabled: true,
    priority: 2,
    config: { port: '/dev/ttyUSB0', frequency: '868' },
  },
  {
    id: 'cellular',
    name: '4G/LTE',
    enabled: true,
    priority: 3,
    config: { apn: 'internet', pin: '••••' },
  },
  {
    id: 'ble',
    name: 'Bluetooth',
    enabled: false,
    priority: 4,
    config: { device: 'hci0' },
  },
];

const mockCloudEndpoints: CloudEndpoint[] = [
  {
    id: 'hashcat',
    name: 'Hashcat GPU VPS',
    url: 'https://crack.example.com',
    apiKey: 'sk_live_xxxx...xxxx',
    status: 'connected',
  },
  {
    id: 'evilginx',
    name: 'Evilginx VPS',
    url: 'https://phish.example.com',
    apiKey: 'eg_xxxx...xxxx',
    status: 'connected',
  },
  {
    id: 'storage',
    name: 'Cloud Storage',
    url: 'https://s3.example.com',
    apiKey: 'aws_xxxx...xxxx',
    status: 'error',
  },
];

const channelIcons: Record<string, React.ElementType> = {
  wifi: Wifi,
  lora: Radio,
  cellular: Signal,
  ble: Bluetooth,
};

type SettingsTab = 'channels' | 'cloud' | 'security' | 'notifications' | 'system' | 'appearance';

export function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('channels');
  const [channels, setChannels] = useState(mockChannels);
  const [showApiKeys, setShowApiKeys] = useState<Set<string>>(new Set());
  const [isSaving, setIsSaving] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);

  const tabs: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
    { id: 'channels', label: 'Channels', icon: Radio },
    { id: 'cloud', label: 'Cloud', icon: Cloud },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'system', label: 'System', icon: Database },
  ];

  const toggleChannel = (id: string) => {
    setChannels(
      channels.map((ch) =>
        ch.id === id ? { ...ch, enabled: !ch.enabled } : ch
      )
    );
  };

  const toggleApiKeyVisibility = (id: string) => {
    const newSet = new Set(showApiKeys);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setShowApiKeys(newSet);
  };

  const handleSave = async () => {
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-border-default pb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg transition-all',
              activeTab === tab.id
                ? 'bg-neon-green/10 text-neon-green border border-neon-green/30'
                : 'text-text-secondary hover:text-text-primary hover:bg-nexus-elevated'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Channels Tab */}
      {activeTab === 'channels' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Communication Channels
            </h3>
            <div className="space-y-4">
              {channels.map((channel) => {
                const Icon = channelIcons[channel.id] || Radio;
                return (
                  <div
                    key={channel.id}
                    className={cn(
                      'p-4 rounded-lg border transition-all',
                      channel.enabled
                        ? 'bg-nexus-elevated border-neon-green/30'
                        : 'bg-nexus-surface border-border-default opacity-60'
                    )}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            'w-10 h-10 rounded-lg flex items-center justify-center',
                            channel.enabled
                              ? 'bg-neon-green/10'
                              : 'bg-nexus-hover'
                          )}
                        >
                          <Icon
                            className={cn(
                              'w-5 h-5',
                              channel.enabled ? 'text-neon-green' : 'text-text-muted'
                            )}
                          />
                        </div>
                        <div>
                          <h4 className="font-mono font-semibold">{channel.name}</h4>
                          <p className="text-xs text-text-muted">
                            Priority: {channel.priority}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => toggleChannel(channel.id)}
                        className={cn(
                          'relative w-12 h-6 rounded-full transition-all',
                          channel.enabled ? 'bg-neon-green' : 'bg-nexus-hover'
                        )}
                      >
                        <div
                          className={cn(
                            'absolute top-1 w-4 h-4 rounded-full bg-white transition-all',
                            channel.enabled ? 'left-7' : 'left-1'
                          )}
                        />
                      </button>
                    </div>

                    {channel.enabled && (
                      <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-border-default">
                        {Object.entries(channel.config).map(([key, value]) => (
                          <div key={key}>
                            <label className="text-xs text-text-muted capitalize">
                              {key}
                            </label>
                            <input
                              type={key.includes('password') || key.includes('pin') ? 'password' : 'text'}
                              defaultValue={value}
                              className="w-full mt-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                                         text-sm font-mono focus:outline-none focus:border-neon-cyan"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Cloud Tab */}
      {activeTab === 'cloud' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Cloud Endpoints
            </h3>
            <div className="space-y-4">
              {mockCloudEndpoints.map((endpoint) => (
                <div
                  key={endpoint.id}
                  className="p-4 bg-nexus-elevated rounded-lg border border-border-default"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <Server className="w-5 h-5 text-neon-cyan" />
                      <div>
                        <h4 className="font-mono font-semibold">{endpoint.name}</h4>
                        <p className="text-xs text-text-muted font-mono">
                          {endpoint.url}
                        </p>
                      </div>
                    </div>
                    <span
                      className={cn(
                        'badge',
                        endpoint.status === 'connected' && 'badge-online',
                        endpoint.status === 'error' && 'badge-offline',
                        endpoint.status === 'unknown' && 'badge-pending'
                      )}
                    >
                      {endpoint.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Key className="w-4 h-4 text-text-muted" />
                    <code className="flex-1 text-sm font-mono text-text-secondary">
                      {showApiKeys.has(endpoint.id)
                        ? endpoint.apiKey
                        : '••••••••••••••••'}
                    </code>
                    <button
                      onClick={() => toggleApiKeyVisibility(endpoint.id)}
                      className="btn-icon p-1"
                    >
                      {showApiKeys.has(endpoint.id) ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button className="btn-secondary mt-4 w-full">
              + Add Endpoint
            </button>
          </div>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Authentication
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-text-muted">Username</label>
                <div className="flex items-center gap-2 mt-1">
                  <User className="w-4 h-4 text-text-muted" />
                  <input
                    type="text"
                    defaultValue="admin"
                    className="flex-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                               font-mono focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm text-text-muted">Current Password</label>
                <div className="flex items-center gap-2 mt-1">
                  <Key className="w-4 h-4 text-text-muted" />
                  <input
                    type="password"
                    placeholder="••••••••"
                    className="flex-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                               font-mono focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm text-text-muted">New Password</label>
                <div className="flex items-center gap-2 mt-1">
                  <Key className="w-4 h-4 text-text-muted" />
                  <input
                    type="password"
                    placeholder="••••••••"
                    className="flex-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                               font-mono focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              API Keys
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-nexus-elevated rounded-lg">
                <div>
                  <p className="font-mono text-sm">Primary API Key</p>
                  <code className="text-xs text-text-muted">
                    nx_live_xxxxxxxxxxxx
                  </code>
                </div>
                <button className="btn-secondary text-sm">Regenerate</button>
              </div>
              <div className="flex items-center justify-between p-3 bg-nexus-elevated rounded-lg">
                <div>
                  <p className="font-mono text-sm">Read-Only Key</p>
                  <code className="text-xs text-text-muted">
                    nx_ro_xxxxxxxxxxxx
                  </code>
                </div>
                <button className="btn-secondary text-sm">Regenerate</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          {/* Ntfy.sh Configuration */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-neon-cyan/10 flex items-center justify-center">
                  <Bell className="w-5 h-5 text-neon-cyan" />
                </div>
                <div>
                  <h3 className="font-mono font-semibold text-text-primary">Ntfy.sh Push Notifications</h3>
                  <p className="text-xs text-text-muted">Self-hosted push notifications (OPSEC-safe)</p>
                </div>
              </div>
              <button
                className={cn(
                  'relative w-12 h-6 rounded-full transition-all',
                  'bg-neon-green'
                )}
              >
                <div className="absolute top-1 left-7 w-4 h-4 rounded-full bg-white transition-all" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm text-text-muted">Server URL</label>
                <input
                  type="text"
                  defaultValue="https://ntfy.sh"
                  placeholder="https://ntfy.your-server.com"
                  className="w-full mt-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                             text-sm font-mono focus:outline-none focus:border-neon-cyan"
                />
                <p className="text-xs text-text-muted mt-1">
                  Use ntfy.sh (public) or self-host for OPSEC
                </p>
              </div>
              
              <div>
                <label className="text-sm text-text-muted">Topic</label>
                <input
                  type="text"
                  defaultValue="momo-alerts"
                  placeholder="your-secret-topic"
                  className="w-full mt-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                             text-sm font-mono focus:outline-none focus:border-neon-cyan"
                />
                <p className="text-xs text-text-muted mt-1">
                  Use a random topic name for privacy
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-text-muted">Access Token (optional)</label>
                  <input
                    type="password"
                    placeholder="tk_xxxxxxxx"
                    className="w-full mt-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                               text-sm font-mono focus:outline-none focus:border-neon-cyan"
                  />
                </div>
                <div>
                  <label className="text-sm text-text-muted">Min. Severity</label>
                  <select
                    defaultValue="medium"
                    className="w-full mt-1 px-3 py-2 bg-nexus-bg border border-border-default rounded
                               text-sm font-mono focus:outline-none focus:border-neon-cyan"
                  >
                    <option value="critical">Critical only</option>
                    <option value="high">High+</option>
                    <option value="medium">Medium+</option>
                    <option value="low">Low+</option>
                    <option value="info">All</option>
                  </select>
                </div>
              </div>
              
              <button
                onClick={() => nexusToast.success('Test notification sent!')}
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                <Bell className="w-4 h-4" />
                Send Test Notification
              </button>
            </div>
          </div>

          {/* Alert Types */}
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Alert Types
            </h3>
            <div className="space-y-4">
              {[
                { id: 'handshake', label: 'Handshake Captured', emoji: '🤝', enabled: true },
                { id: 'crack', label: 'Password Cracked', emoji: '🔓', enabled: true },
                { id: 'credential', label: 'Credential Captured', emoji: '🎣', enabled: true },
                { id: 'device_offline', label: 'Device Offline', emoji: '⚠️', enabled: true },
                { id: 'low_battery', label: 'Low Battery Warning', emoji: '🔋', enabled: true },
                { id: 'phishing_session', label: 'Phishing Session', emoji: '🎭', enabled: true },
                { id: 'system_alert', label: 'System Alerts', emoji: '🚨', enabled: false },
              ].map((notif) => (
                <div
                  key={notif.id}
                  className="flex items-center justify-between p-3 bg-nexus-elevated rounded-lg"
                >
                  <span className="text-sm">
                    <span className="mr-2">{notif.emoji}</span>
                    {notif.label}
                  </span>
                  <button
                    className={cn(
                      'relative w-12 h-6 rounded-full transition-all',
                      notif.enabled ? 'bg-neon-green' : 'bg-nexus-hover'
                    )}
                  >
                    <div
                      className={cn(
                        'absolute top-1 w-4 h-4 rounded-full bg-white transition-all',
                        notif.enabled ? 'left-7' : 'left-1'
                      )}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* LoRa Notifications */}
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              LoRa/Meshtastic Notifications
            </h3>
            <p className="text-sm text-text-muted mb-4">
              Send notifications via LoRa mesh network (off-grid)
            </p>
            <div className="flex items-center justify-between p-3 bg-nexus-elevated rounded-lg">
              <span className="text-sm">Enable LoRa Notifications</span>
              <button className="relative w-12 h-6 rounded-full transition-all bg-neon-green">
                <div className="absolute top-1 left-7 w-4 h-4 rounded-full bg-white transition-all" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Appearance Tab */}
      {activeTab === 'appearance' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Theme
            </h3>
            <div className="flex items-center justify-between p-4 bg-nexus-elevated rounded-lg">
              <div>
                <p className="font-medium">Color Theme</p>
                <p className="text-sm text-text-muted">
                  Choose between dark, light, or system theme
                </p>
              </div>
              <ThemeToggle showLabel />
            </div>
          </div>

          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Keyboard Shortcuts
            </h3>
            <p className="text-sm text-text-muted mb-4">
              Use keyboard shortcuts for faster navigation
            </p>
            <button
              onClick={() => setShowShortcuts(true)}
              className="btn-secondary flex items-center gap-2"
            >
              <Keyboard className="w-4 h-4" />
              View All Shortcuts
            </button>
          </div>

          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Export Data
            </h3>
            <p className="text-sm text-text-muted mb-4">
              Export captured data to CSV or JSON format
            </p>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  // Mock data for demo
                  exportDevices([
                    { id: 'momo-001', name: 'MoMo Alpha', type: 'momo', status: 'online', lastSeen: new Date().toISOString(), battery: 85 },
                    { id: 'ghost-001', name: 'Ghost Pi', type: 'ghostbridge', status: 'online', lastSeen: new Date().toISOString() },
                  ], 'csv');
                  nexusToast.success('Devices exported to CSV');
                }}
                className="btn-secondary flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Devices
              </button>
              <button
                onClick={() => {
                  exportHandshakes([
                    { id: '1', ssid: 'CORP-WiFi', bssid: 'AA:BB:CC:DD:EE:FF', capturedAt: new Date().toISOString(), status: 'cracked', cracked: true, password: 'password123', deviceId: 'momo-001' },
                  ], 'csv');
                  nexusToast.success('Handshakes exported to CSV');
                }}
                className="btn-secondary flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Handshakes
              </button>
              <button
                onClick={() => {
                  exportCrackJobs([
                    { id: '1', ssid: 'CORP-WiFi', status: 'completed', progress: 100, startedAt: new Date().toISOString(), completedAt: new Date().toISOString(), password: 'password123' },
                  ], 'csv');
                  nexusToast.success('Crack jobs exported to CSV');
                }}
                className="btn-secondary flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Crack Jobs
              </button>
              <button
                onClick={() => {
                  exportSessions([
                    { id: '1', phishlet: 'o365', username: 'user@corp.com', ip: '192.168.1.100', capturedAt: new Date().toISOString() },
                  ], 'csv');
                  nexusToast.success('Sessions exported to CSV');
                }}
                className="btn-secondary flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                Sessions
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Keyboard Shortcuts Modal */}
      <Modal
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
        title="Keyboard Shortcuts"
        size="md"
      >
        <KeyboardShortcutsList />
      </Modal>

      {/* System Tab */}
      {activeTab === 'system' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              System Information
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-nexus-elevated rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Server className="w-4 h-4 text-neon-cyan" />
                  <span className="text-xs text-text-muted">Version</span>
                </div>
                <p className="font-mono">Nexus v1.0.0</p>
              </div>
              <div className="p-3 bg-nexus-elevated rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Clock className="w-4 h-4 text-neon-green" />
                  <span className="text-xs text-text-muted">Uptime</span>
                </div>
                <p className="font-mono">3d 14h 22m</p>
              </div>
              <div className="p-3 bg-nexus-elevated rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <HardDrive className="w-4 h-4 text-neon-orange" />
                  <span className="text-xs text-text-muted">Storage</span>
                </div>
                <p className="font-mono">12.4 / 64 GB</p>
              </div>
              <div className="p-3 bg-nexus-elevated rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Database className="w-4 h-4 text-neon-magenta" />
                  <span className="text-xs text-text-muted">Database</span>
                </div>
                <p className="font-mono">2,451 records</p>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Maintenance
            </h3>
            <div className="space-y-3">
              <button className="btn-secondary w-full flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4" />
                Restart Nexus
              </button>
              <button className="btn-secondary w-full flex items-center justify-center gap-2">
                <Database className="w-4 h-4" />
                Backup Database
              </button>
              <button className="btn-danger w-full flex items-center justify-center gap-2">
                <Trash2 className="w-4 h-4" />
                Clear All Data
              </button>
            </div>
          </div>

          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              System Logs
            </h3>
            <div className="terminal max-h-48 overflow-y-auto text-xs">
              <pre className="text-neon-green">
{`[2025-12-20 14:32:15] INFO  - Nexus started
[2025-12-20 14:32:16] INFO  - WiFi channel connected
[2025-12-20 14:32:18] INFO  - LoRa channel connected
[2025-12-20 14:32:20] INFO  - 4G channel connected
[2025-12-20 14:35:00] INFO  - Device momo-001 registered
[2025-12-20 14:35:05] INFO  - Handshake received from momo-001
[2025-12-20 14:40:00] INFO  - Heartbeat from ghost-001
[2025-12-20 15:00:00] WARN  - Low battery on mimic-001 (15%)
[2025-12-20 15:30:00] INFO  - Crack job completed: CORP-WiFi`}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end gap-4">
        <button className="btn-secondary">Cancel</button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary flex items-center gap-2"
        >
          {isSaving ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save Changes
            </>
          )}
        </button>
      </div>
    </div>
  );
}


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
} from 'lucide-react';
import { cn } from '../lib/utils';

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

type SettingsTab = 'channels' | 'cloud' | 'security' | 'notifications' | 'system';

export function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('channels');
  const [channels, setChannels] = useState(mockChannels);
  const [showApiKeys, setShowApiKeys] = useState<Set<string>>(new Set());
  const [isSaving, setIsSaving] = useState(false);

  const tabs: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
    { id: 'channels', label: 'Channels', icon: Radio },
    { id: 'cloud', label: 'Cloud', icon: Cloud },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
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
          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              Notification Preferences
            </h3>
            <div className="space-y-4">
              {[
                { id: 'handshake', label: 'Handshake Captured', enabled: true },
                { id: 'crack', label: 'Password Cracked', enabled: true },
                { id: 'device_offline', label: 'Device Offline', enabled: true },
                { id: 'low_battery', label: 'Low Battery Warning', enabled: true },
                { id: 'phishing_session', label: 'Phishing Session', enabled: true },
                { id: 'system_alert', label: 'System Alerts', enabled: false },
              ].map((notif) => (
                <div
                  key={notif.id}
                  className="flex items-center justify-between p-3 bg-nexus-elevated rounded-lg"
                >
                  <span className="text-sm">{notif.label}</span>
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

          <div className="card">
            <h3 className="font-mono font-semibold text-text-primary mb-4">
              LoRa Notifications
            </h3>
            <p className="text-sm text-text-muted mb-4">
              Send notifications to operator phone via LoRa/Meshtastic
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


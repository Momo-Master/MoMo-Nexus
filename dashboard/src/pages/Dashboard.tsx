import { useState, lazy, Suspense } from 'react';
import { Radio, Fingerprint, KeyRound, AlertTriangle, Map as MapIcon } from 'lucide-react';
import { StatCard } from '../components/ui/StatCard';
import { ActivityFeed } from '../components/ui/ActivityFeed';
import { DeviceCard } from '../components/ui/DeviceCard';
import { DeviceDetailModal } from '../components/ui/DeviceDetailModal';
import { nexusToast } from '../components/ui/Toast';
import type { Device, Activity, Stats } from '../types';

// Lazy load map to prevent React 18 Strict Mode double-init issue
const DeviceMap = lazy(() => import('../components/ui/DeviceMap').then(m => ({ default: m.DeviceMap })));

// Mock data - will be replaced with API calls
const mockStats: Stats = {
  devicesOnline: 3,
  devicesTotal: 4,
  handshakesTotal: 47,
  handshakesToday: 8,
  crackedTotal: 12,
  crackedToday: 3,
  alertsActive: 2,
};

const mockDevices: Device[] = [
  {
    id: 'momo-001',
    name: 'MoMo-Alpha',
    type: 'momo',
    status: 'online',
    lastSeen: new Date(Date.now() - 30000).toISOString(),
    battery: 78,
    temperature: 52,
    location: { lat: 41.0082, lon: 28.9784 },
    stats: { captures: 23, uptime: 14400 },
    channel: 'wifi',
  },
  {
    id: 'ghost-001',
    name: 'Ghost-HQ',
    type: 'ghostbridge',
    status: 'online',
    lastSeen: new Date(Date.now() - 120000).toISOString(),
    temperature: 45,
    stats: { captures: 0, uptime: 86400 },
    channel: 'cellular',
  },
  {
    id: 'mimic-001',
    name: 'Mimic-USB',
    type: 'mimic',
    status: 'offline',
    lastSeen: new Date(Date.now() - 3600000).toISOString(),
    stats: { captures: 5, uptime: 0 },
    channel: 'wifi',
  },
];

const mockActivities: Activity[] = [
  {
    id: '1',
    type: 'handshake',
    icon: '🤝',
    message: 'Handshake captured: CORP-WiFi-5G',
    timestamp: new Date(Date.now() - 120000).toISOString(),
    color: 'green',
  },
  {
    id: '2',
    type: 'crack',
    icon: '🔓',
    message: 'Password cracked: guest_network',
    timestamp: new Date(Date.now() - 300000).toISOString(),
    color: 'magenta',
  },
  {
    id: '3',
    type: 'device',
    icon: '📡',
    message: 'MoMo-Alpha connected via WiFi',
    timestamp: new Date(Date.now() - 600000).toISOString(),
    color: 'cyan',
  },
  {
    id: '4',
    type: 'alert',
    icon: '⚠️',
    message: 'Low battery on Mimic-USB (15%)',
    timestamp: new Date(Date.now() - 900000).toISOString(),
    color: 'orange',
  },
  {
    id: '5',
    type: 'credential',
    icon: '🔑',
    message: 'EAP credential: john@corp.local',
    timestamp: new Date(Date.now() - 1200000).toISOString(),
    color: 'green',
  },
  {
    id: '6',
    type: 'handshake',
    icon: '🤝',
    message: 'PMKID captured: HomeNetwork',
    timestamp: new Date(Date.now() - 1800000).toISOString(),
    color: 'green',
  },
];

export function Dashboard() {
  const [showMap, setShowMap] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  
  const handleDeviceClick = (device: Device) => {
    setSelectedDevice(device);
  };

  const handleReboot = (deviceId: string) => {
    nexusToast.info(`Rebooting ${deviceId}...`);
  };

  const handleScan = (deviceId: string) => {
    nexusToast.success(`Scan started on ${deviceId}`);
  };

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Devices Online"
          value={`${mockStats.devicesOnline}/${mockStats.devicesTotal}`}
          icon={<Radio className="w-6 h-6" />}
          color="cyan"
        />
        <StatCard
          label="Total Captures"
          value={mockStats.handshakesTotal}
          icon={<Fingerprint className="w-6 h-6" />}
          trend={{ value: 12, isPositive: true }}
          color="green"
        />
        <StatCard
          label="Cracked"
          value={mockStats.crackedTotal}
          icon={<KeyRound className="w-6 h-6" />}
          trend={{ value: 25, isPositive: true }}
          color="magenta"
        />
        <StatCard
          label="Active Alerts"
          value={mockStats.alertsActive}
          icon={<AlertTriangle className="w-6 h-6" />}
          color="orange"
        />
      </div>

      {/* Map Toggle */}
      <div className="flex items-center justify-between">
        <h2 className="font-mono font-semibold text-text-primary">
          Fleet Status
        </h2>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowMap(!showMap)}
            className={`btn-icon flex items-center gap-2 px-3 py-1.5 rounded ${
              showMap ? 'bg-neon-cyan/10 text-neon-cyan' : ''
            }`}
          >
            <MapIcon className="w-4 h-4" />
            {showMap ? 'Hide Map' : 'Show Map'}
          </button>
          <a
            href="/fleet"
            className="text-sm text-neon-cyan hover:text-neon-cyan/80"
          >
            View all →
          </a>
        </div>
      </div>

      {/* Device Map */}
      {showMap && (
        <Suspense fallback={
          <div className="h-64 rounded-lg border border-border-default bg-nexus-surface flex items-center justify-center">
            <div className="text-text-muted animate-pulse">Loading map...</div>
          </div>
        }>
          <DeviceMap
            devices={mockDevices}
            className="h-64"
            onDeviceClick={handleDeviceClick}
          />
        </Suspense>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Devices */}
        <div className="lg:col-span-2 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {mockDevices.map((device) => (
              <DeviceCard 
                key={device.id} 
                device={device} 
                onClick={() => handleDeviceClick(device)}
              />
            ))}
          </div>
        </div>

        {/* Activity Feed */}
        <div>
          <ActivityFeed activities={mockActivities} />
        </div>
      </div>

      {/* Bottom Section - Quick Actions */}
      <div className="card">
        <h3 className="font-mono font-semibold text-text-primary mb-4">
          Quick Actions
        </h3>
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary" onClick={() => nexusToast.info('Scanning networks...')}>
            <span className="flex items-center gap-2">
              <Radio className="w-4 h-4" />
              Scan Networks
            </span>
          </button>
          <button className="btn-secondary" onClick={() => nexusToast.success('Capture started!')}>
            <span className="flex items-center gap-2">
              <Fingerprint className="w-4 h-4" />
              Start Capture
            </span>
          </button>
          <button className="btn-secondary" onClick={() => nexusToast.info('Submitting to crack queue...')}>
            <span className="flex items-center gap-2">
              <KeyRound className="w-4 h-4" />
              Submit to Crack
            </span>
          </button>
        </div>
      </div>

      {/* Device Detail Modal */}
      <DeviceDetailModal
        device={selectedDevice}
        isOpen={!!selectedDevice}
        onClose={() => setSelectedDevice(null)}
        onReboot={handleReboot}
        onScan={handleScan}
      />
    </div>
  );
}


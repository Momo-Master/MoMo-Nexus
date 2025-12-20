import {
  Radio,
  Ghost,
  Drama,
  Server,
  Battery,
  Thermometer,
  MapPin,
  Clock,
  Wifi,
  Signal,
  Antenna,
  Bluetooth,
  RefreshCw,
  Power,
  Settings,
  Terminal,
} from 'lucide-react';
import { Modal } from './Modal';
import { cn } from '../../lib/utils';
import { formatRelativeTime } from '../../lib/utils';
import type { Device } from '../../types';

const deviceIcons: Record<string, React.ElementType> = {
  momo: Radio,
  ghostbridge: Ghost,
  mimic: Drama,
  nexus: Server,
};

const channelIcons: Record<string, React.ElementType> = {
  wifi: Wifi,
  cellular: Signal,
  lora: Antenna,
  ble: Bluetooth,
};

interface DeviceDetailModalProps {
  device: Device | null;
  isOpen: boolean;
  onClose: () => void;
  onReboot?: (deviceId: string) => void;
  onScan?: (deviceId: string) => void;
}

export function DeviceDetailModal({
  device,
  isOpen,
  onClose,
  onReboot,
  onScan,
}: DeviceDetailModalProps) {
  if (!device) return null;

  const DeviceIcon = deviceIcons[device.type] || Radio;
  const ChannelIcon = channelIcons[device.channel] || Wifi;

  const uptimeHours = Math.floor(device.stats.uptime / 3600);
  const uptimeMinutes = Math.floor((device.stats.uptime % 3600) / 60);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div
            className={cn(
              'w-16 h-16 rounded-xl flex items-center justify-center',
              device.status === 'online'
                ? 'bg-neon-green/10 border border-neon-green/30'
                : 'bg-nexus-elevated border border-border-default'
            )}
          >
            <DeviceIcon
              className={cn(
                'w-8 h-8',
                device.status === 'online' ? 'text-neon-green' : 'text-text-muted'
              )}
            />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="font-mono font-bold text-xl text-text-primary">
                {device.name}
              </h2>
              <span
                className={cn(
                  'badge',
                  device.status === 'online' && 'badge-online',
                  device.status === 'offline' && 'badge-offline',
                  device.status === 'degraded' && 'badge-warning'
                )}
              >
                {device.status}
              </span>
            </div>
            <p className="text-text-muted capitalize">{device.type}</p>
            <p className="text-xs text-text-muted mt-1">
              ID: <code className="font-mono">{device.id}</code>
            </p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* Battery */}
          {device.battery !== undefined && (
            <div className="p-3 bg-nexus-elevated rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <Battery
                  className={cn(
                    'w-4 h-4',
                    device.battery > 50
                      ? 'text-neon-green'
                      : device.battery > 20
                      ? 'text-neon-orange'
                      : 'text-neon-red'
                  )}
                />
                <span className="text-xs text-text-muted">Battery</span>
              </div>
              <p className="font-mono text-lg font-semibold">{device.battery}%</p>
            </div>
          )}

          {/* Temperature */}
          {device.temperature !== undefined && (
            <div className="p-3 bg-nexus-elevated rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <Thermometer
                  className={cn(
                    'w-4 h-4',
                    device.temperature < 60
                      ? 'text-neon-green'
                      : device.temperature < 75
                      ? 'text-neon-orange'
                      : 'text-neon-red'
                  )}
                />
                <span className="text-xs text-text-muted">Temperature</span>
              </div>
              <p className="font-mono text-lg font-semibold">{device.temperature}°C</p>
            </div>
          )}

          {/* Uptime */}
          <div className="p-3 bg-nexus-elevated rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-neon-cyan" />
              <span className="text-xs text-text-muted">Uptime</span>
            </div>
            <p className="font-mono text-lg font-semibold">
              {uptimeHours}h {uptimeMinutes}m
            </p>
          </div>

          {/* Captures */}
          <div className="p-3 bg-nexus-elevated rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Radio className="w-4 h-4 text-neon-magenta" />
              <span className="text-xs text-text-muted">Captures</span>
            </div>
            <p className="font-mono text-lg font-semibold text-neon-green">
              {device.stats.captures}
            </p>
          </div>
        </div>

        {/* Connection Info */}
        <div className="p-4 bg-nexus-elevated rounded-lg">
          <h3 className="font-mono font-semibold text-sm text-text-muted mb-3">
            Connection
          </h3>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ChannelIcon className="w-5 h-5 text-neon-cyan" />
              <div>
                <p className="font-semibold capitalize">{device.channel}</p>
                <p className="text-xs text-text-muted">
                  Last seen: {formatRelativeTime(device.lastSeen)}
                </p>
              </div>
            </div>
            <div
              className={cn(
                'w-3 h-3 rounded-full',
                device.status === 'online' && 'bg-neon-green animate-pulse',
                device.status === 'offline' && 'bg-neon-red',
                device.status === 'degraded' && 'bg-neon-orange animate-pulse'
              )}
            />
          </div>
        </div>

        {/* Location */}
        {device.location && (
          <div className="p-4 bg-nexus-elevated rounded-lg">
            <h3 className="font-mono font-semibold text-sm text-text-muted mb-3">
              Location
            </h3>
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5 text-neon-cyan" />
              <div>
                <p className="font-mono">
                  {device.location.lat.toFixed(6)}, {device.location.lon.toFixed(6)}
                </p>
                <p className="text-xs text-text-muted">GPS coordinates</p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-3 pt-4 border-t border-border-default">
          <button
            onClick={() => onScan?.(device.id)}
            className="btn-primary flex items-center gap-2"
            disabled={device.status === 'offline'}
          >
            <RefreshCw className="w-4 h-4" />
            Start Scan
          </button>
          <button
            onClick={() => onReboot?.(device.id)}
            className="btn-secondary flex items-center gap-2"
            disabled={device.status === 'offline'}
          >
            <Power className="w-4 h-4" />
            Reboot
          </button>
          <button className="btn-secondary flex items-center gap-2">
            <Terminal className="w-4 h-4" />
            Console
          </button>
          <button className="btn-secondary flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Configure
          </button>
        </div>
      </div>
    </Modal>
  );
}


import {
  Radio,
  Ghost,
  Drama,
  Server,
  Battery,
  Thermometer,
  MapPin,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { formatRelativeTime } from '../../lib/utils';
import type { Device } from '../../types';

const deviceIcons: Record<string, React.ElementType> = {
  momo: Radio,
  ghostbridge: Ghost,
  mimic: Drama,
  nexus: Server,
};

const deviceColors: Record<string, string> = {
  momo: 'neon-cyan',
  ghostbridge: 'neon-magenta',
  mimic: 'neon-orange',
  nexus: 'neon-green',
};

interface DeviceCardProps {
  device: Device;
  onClick?: () => void;
}

export function DeviceCard({ device, onClick }: DeviceCardProps) {
  const Icon = deviceIcons[device.type] || Radio;
  const color = deviceColors[device.type] || 'neon-green';

  return (
    <div
      className={cn(
        'card cursor-pointer',
        'hover:border-' + color + '/30',
        'hover:shadow-' + color
      )}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-lg border flex items-center justify-center',
              `bg-${color}/10 border-${color}/30`
            )}
          >
            <Icon className={cn('w-5 h-5', `text-${color}`)} />
          </div>
          <div>
            <h4 className="font-mono font-semibold text-text-primary">
              {device.name}
            </h4>
            <p className="text-xs text-text-muted capitalize">{device.type}</p>
          </div>
        </div>
        <div
          className={cn(
            'px-2 py-1 rounded-full text-xs font-medium',
            device.status === 'online' && 'badge-online',
            device.status === 'offline' && 'badge-offline',
            device.status === 'degraded' && 'badge-warning'
          )}
        >
          <div className="flex items-center gap-1.5">
            <div
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                device.status === 'online' && 'bg-neon-green',
                device.status === 'offline' && 'bg-neon-red',
                device.status === 'degraded' && 'bg-neon-orange'
              )}
            />
            {device.status}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        {device.battery !== undefined && (
          <div className="flex items-center gap-2 text-sm">
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
            <span className="text-text-secondary">{device.battery}%</span>
          </div>
        )}
        {device.temperature !== undefined && (
          <div className="flex items-center gap-2 text-sm">
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
            <span className="text-text-secondary">{device.temperature}°C</span>
          </div>
        )}
        {device.location && (
          <div className="flex items-center gap-2 text-sm">
            <MapPin className="w-4 h-4 text-neon-cyan" />
            <span className="text-text-secondary">GPS</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-border-default">
        <div className="text-sm">
          <span className="text-text-muted">Captures: </span>
          <span className="text-neon-green font-mono">{device.stats.captures}</span>
        </div>
        <p className="text-xs text-text-muted">
          {formatRelativeTime(device.lastSeen)}
        </p>
      </div>
    </div>
  );
}


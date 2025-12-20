import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Radio,
  Fingerprint,
  KeyRound,
  Fish,
  BarChart3,
  Settings,
  Wifi,
  Signal,
  Antenna,
  Bluetooth,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import type { ChannelStatus } from '../../types';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Fleet', href: '/fleet', icon: Radio },
  { name: 'Captures', href: '/captures', icon: Fingerprint },
  { name: 'Cracking', href: '/cracking', icon: KeyRound },
  { name: 'Phishing', href: '/phishing', icon: Fish },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
];

const channelIcons: Record<string, React.ElementType> = {
  wifi: Wifi,
  cellular: Signal,
  lora: Antenna,
  ble: Bluetooth,
};

interface SidebarProps {
  channels?: ChannelStatus[];
}

export function Sidebar({ channels = [] }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-nexus-surface border-r border-border-default flex flex-col z-50">
      {/* Logo */}
      <div className="p-6 border-b border-border-default">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-neon-green/10 border border-neon-green/30 flex items-center justify-center">
            <span className="text-neon-green font-mono font-bold text-lg">N</span>
          </div>
          <div>
            <h1 className="font-mono font-bold text-lg text-text-primary tracking-wider">
              NEXUS
            </h1>
            <p className="text-xs text-text-muted">Control Center</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                'text-text-secondary hover:text-text-primary hover:bg-nexus-elevated',
                isActive && 'text-neon-green bg-neon-green/10 border-l-2 border-neon-green'
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* Channel Status */}
      <div className="p-4 border-t border-border-default">
        <h3 className="text-xs text-text-muted uppercase tracking-wider mb-3 px-2">
          Channels
        </h3>
        <div className="space-y-2">
          {channels.length > 0 ? (
            channels.map((channel) => {
              const Icon = channelIcons[channel.type] || Wifi;
              return (
                <div
                  key={channel.type}
                  className="flex items-center justify-between px-2 py-1.5"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-text-secondary" />
                    <span className="text-sm text-text-secondary capitalize">
                      {channel.type}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-text-muted font-mono">
                      {channel.latency}ms
                    </span>
                    <div
                      className={cn(
                        'w-2 h-2 rounded-full',
                        channel.status === 'up' && 'bg-neon-green',
                        channel.status === 'degraded' && 'bg-neon-orange',
                        channel.status === 'down' && 'bg-neon-red'
                      )}
                    />
                  </div>
                </div>
              );
            })
          ) : (
            // Default channels when no data
            ['wifi', 'lora', 'cellular', 'ble'].map((type) => {
              const Icon = channelIcons[type];
              return (
                <div
                  key={type}
                  className="flex items-center justify-between px-2 py-1.5"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-text-secondary" />
                    <span className="text-sm text-text-secondary capitalize">
                      {type}
                    </span>
                  </div>
                  <div className="w-2 h-2 rounded-full bg-text-muted" />
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Version */}
      <div className="p-4 border-t border-border-default">
        <p className="text-xs text-text-muted text-center font-mono">
          Nexus v1.0.0
        </p>
      </div>
    </aside>
  );
}


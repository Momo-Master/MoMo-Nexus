import { Bell, Wifi, WifiOff, Menu } from 'lucide-react';
import { cn } from '../../lib/utils';

interface HeaderProps {
  title: string;
  subtitle?: string;
  isConnected?: boolean;
  alertCount?: number;
  onMenuClick?: () => void;
}

export function Header({
  title,
  subtitle,
  isConnected = true,
  alertCount = 0,
  onMenuClick,
}: HeaderProps) {
  return (
    <header className="h-16 bg-nexus-surface border-b border-border-default flex items-center justify-between px-6">
      {/* Left side */}
      <div className="flex items-center gap-4">
        {/* Mobile menu button */}
        <button
          onClick={onMenuClick}
          className="lg:hidden btn-icon"
          aria-label="Toggle menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Title */}
        <div>
          <h1 className="text-lg font-mono font-bold text-text-primary">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs text-text-muted">{subtitle}</p>
          )}
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
            isConnected
              ? 'bg-neon-green/10 text-neon-green'
              : 'bg-neon-red/10 text-neon-red'
          )}
        >
          {isConnected ? (
            <>
              <Wifi className="w-4 h-4" />
              <span className="hidden sm:inline font-mono">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4" />
              <span className="hidden sm:inline font-mono">Offline</span>
            </>
          )}
        </div>

        {/* Alerts */}
        <button className="relative btn-icon">
          <Bell className="w-5 h-5" />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-neon-red text-white text-xs font-bold rounded-full flex items-center justify-center">
              {alertCount > 9 ? '9+' : alertCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}


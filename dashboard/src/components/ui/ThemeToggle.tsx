import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import { cn } from '../../lib/utils';

interface ThemeToggleProps {
  showLabel?: boolean;
  className?: string;
}

export function ThemeToggle({ showLabel = false, className }: ThemeToggleProps) {
  const { theme, toggleTheme, setTheme } = useTheme();

  // Simple toggle button
  if (!showLabel) {
    return (
      <button
        onClick={toggleTheme}
        className={cn(
          'p-2 rounded-lg bg-nexus-elevated hover:bg-nexus-tertiary transition-colors',
          className
        )}
        title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      >
        {theme === 'dark' ? (
          <Sun className="w-5 h-5 text-neon-orange" />
        ) : (
          <Moon className="w-5 h-5 text-neon-cyan" />
        )}
      </button>
    );
  }

  // Extended toggle with options
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="text-sm text-text-secondary">Theme</span>
      <div className="flex items-center bg-nexus-elevated rounded-lg p-1">
        <button
          onClick={() => setTheme('light')}
          className={cn(
            'p-2 rounded transition-colors',
            theme === 'light'
              ? 'bg-neon-green/20 text-neon-green'
              : 'text-text-muted hover:text-text-primary'
          )}
          title="Light mode"
        >
          <Sun className="w-4 h-4" />
        </button>
        <button
          onClick={() => setTheme('dark')}
          className={cn(
            'p-2 rounded transition-colors',
            theme === 'dark'
              ? 'bg-neon-cyan/20 text-neon-cyan'
              : 'text-text-muted hover:text-text-primary'
          )}
          title="Dark mode"
        >
          <Moon className="w-4 h-4" />
        </button>
        <button
          onClick={() => setTheme('system')}
          className={cn(
            'p-2 rounded transition-colors',
            theme === 'system'
              ? 'bg-neon-magenta/20 text-neon-magenta'
              : 'text-text-muted hover:text-text-primary'
          )}
          title="System preference"
        >
          <Monitor className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}


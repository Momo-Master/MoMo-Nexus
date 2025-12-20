import { cn } from '../../lib/utils';
import type { ReactNode } from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: 'green' | 'cyan' | 'magenta' | 'orange' | 'red';
  className?: string;
}

const colorClasses = {
  green: 'text-neon-green',
  cyan: 'text-neon-cyan',
  magenta: 'text-neon-magenta',
  orange: 'text-neon-orange',
  red: 'text-neon-red',
};

const bgClasses = {
  green: 'bg-neon-green/10 border-neon-green/30',
  cyan: 'bg-neon-cyan/10 border-neon-cyan/30',
  magenta: 'bg-neon-magenta/10 border-neon-magenta/30',
  orange: 'bg-neon-orange/10 border-neon-orange/30',
  red: 'bg-neon-red/10 border-neon-red/30',
};

export function StatCard({
  label,
  value,
  icon,
  trend,
  color = 'green',
  className,
}: StatCardProps) {
  return (
    <div className={cn('card-glow', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label">{label}</p>
          <p className={cn('stat-value', colorClasses[color])}>{value}</p>
          {trend && (
            <p
              className={cn(
                'text-sm mt-1',
                trend.isPositive ? 'text-neon-green' : 'text-neon-red'
              )}
            >
              {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}% today
            </p>
          )}
        </div>
        <div
          className={cn(
            'w-12 h-12 rounded-lg border flex items-center justify-center',
            bgClasses[color]
          )}
        >
          <div className={colorClasses[color]}>{icon}</div>
        </div>
      </div>
    </div>
  );
}


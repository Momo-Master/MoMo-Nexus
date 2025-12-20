import {
  Fingerprint,
  KeyRound,
  Radio,
  AlertTriangle,
  Shield,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { formatRelativeTime } from '../../lib/utils';
import type { Activity } from '../../types';

const iconMap: Record<string, React.ElementType> = {
  handshake: Fingerprint,
  crack: KeyRound,
  device: Radio,
  alert: AlertTriangle,
  credential: Shield,
};

const colorClasses = {
  green: 'bg-neon-green/10 text-neon-green',
  cyan: 'bg-neon-cyan/10 text-neon-cyan',
  magenta: 'bg-neon-magenta/10 text-neon-magenta',
  orange: 'bg-neon-orange/10 text-neon-orange',
  red: 'bg-neon-red/10 text-neon-red',
};

interface ActivityFeedProps {
  activities: Activity[];
  maxItems?: number;
}

export function ActivityFeed({ activities, maxItems = 10 }: ActivityFeedProps) {
  const displayActivities = activities.slice(0, maxItems);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-mono font-semibold text-text-primary">
          Live Activity
        </h3>
        <span className="text-xs text-text-muted">
          {activities.length} events
        </span>
      </div>

      <div className="space-y-0 -mx-4">
        {displayActivities.length > 0 ? (
          displayActivities.map((activity) => {
            const Icon = iconMap[activity.type] || AlertTriangle;
            return (
              <div key={activity.id} className="feed-item">
                <div
                  className={cn(
                    'feed-icon',
                    colorClasses[activity.color]
                  )}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">
                    {activity.message}
                  </p>
                  <p className="feed-time">
                    {formatRelativeTime(activity.timestamp)}
                  </p>
                </div>
              </div>
            );
          })
        ) : (
          <div className="px-4 py-8 text-center text-text-muted">
            <p>No recent activity</p>
          </div>
        )}
      </div>
    </div>
  );
}


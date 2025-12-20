import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Radio,
  Fingerprint,
  KeyRound,
  BarChart3,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const navigation = [
  { name: 'Home', href: '/', icon: LayoutDashboard },
  { name: 'Fleet', href: '/fleet', icon: Radio },
  { name: 'Captures', href: '/captures', icon: Fingerprint },
  { name: 'Crack', href: '/cracking', icon: KeyRound },
  { name: 'Stats', href: '/analytics', icon: BarChart3 },
];

export function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-nexus-surface border-t border-border-default lg:hidden">
      <div className="flex items-center justify-around py-2">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-all min-w-[60px]',
                isActive
                  ? 'text-neon-green'
                  : 'text-text-muted hover:text-text-primary'
              )
            }
          >
            {({ isActive }) => (
              <>
                <div
                  className={cn(
                    'p-2 rounded-lg transition-all',
                    isActive && 'bg-neon-green/10'
                  )}
                >
                  <item.icon className="w-5 h-5" />
                </div>
                <span className="text-xs font-medium">{item.name}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
      {/* Safe area for iOS */}
      <div className="h-safe-area-inset-bottom bg-nexus-surface" />
    </nav>
  );
}


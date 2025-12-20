import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { MobileNav } from './MobileNav';
import { ToastProvider } from '../ui/Toast';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';

const pageTitles: Record<string, { title: string; subtitle?: string }> = {
  '/': { title: 'Dashboard', subtitle: 'System Overview' },
  '/fleet': { title: 'Fleet', subtitle: 'Device Management' },
  '/captures': { title: 'Captures', subtitle: 'Handshakes & Credentials' },
  '/cracking': { title: 'Cracking', subtitle: 'Password Recovery' },
  '/phishing': { title: 'Phishing', subtitle: 'Evilginx Sessions' },
  '/analytics': { title: 'Analytics', subtitle: 'Statistics & Reports' },
  '/settings': { title: 'Settings', subtitle: 'Configuration' },
};

export function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  // Enable keyboard shortcuts
  useKeyboardShortcuts();
  
  const pageInfo = pageTitles[location.pathname] || { title: 'Nexus' };

  return (
    <div className="min-h-screen bg-nexus-bg">
      {/* Toast notifications */}
      <ToastProvider />
      
      {/* Sidebar */}
      <Sidebar />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="lg:ml-64 pb-20 lg:pb-0">
        <Header
          title={pageInfo.title}
          subtitle={pageInfo.subtitle}
          isConnected={true}
          alertCount={2}
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
        />
        
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      
      {/* Mobile Bottom Navigation */}
      <MobileNav />
    </div>
  );
}


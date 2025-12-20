import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

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
  
  const pageInfo = pageTitles[location.pathname] || { title: 'Nexus' };

  return (
    <div className="min-h-screen bg-nexus-bg">
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
      <div className="lg:ml-64">
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
    </div>
  );
}


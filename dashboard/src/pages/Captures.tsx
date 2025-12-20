import { useState } from 'react';
import { Search, Filter, Download, Send, Eye, EyeOff } from 'lucide-react';
import { cn } from '../lib/utils';
import type { Handshake } from '../types';

// Mock data
const mockHandshakes: Handshake[] = [
  {
    id: 'hs-001',
    ssid: 'CORP-WiFi-5G',
    bssid: 'AA:BB:CC:DD:EE:01',
    capturedAt: new Date(Date.now() - 120000).toISOString(),
    capturedBy: 'momo-001',
    status: 'cracked',
    password: 'corporate2024!',
    security: 'WPA2',
    signal: -45,
  },
  {
    id: 'hs-002',
    ssid: 'HomeNetwork_2G',
    bssid: 'AA:BB:CC:DD:EE:02',
    capturedAt: new Date(Date.now() - 300000).toISOString(),
    capturedBy: 'momo-001',
    status: 'cracking',
    security: 'WPA2',
    signal: -62,
  },
  {
    id: 'hs-003',
    ssid: 'Starbucks_Guest',
    bssid: 'AA:BB:CC:DD:EE:03',
    capturedAt: new Date(Date.now() - 600000).toISOString(),
    capturedBy: 'momo-002',
    status: 'pending',
    security: 'WPA2',
    signal: -55,
  },
  {
    id: 'hs-004',
    ssid: 'SecureNet_WPA3',
    bssid: 'AA:BB:CC:DD:EE:04',
    capturedAt: new Date(Date.now() - 900000).toISOString(),
    capturedBy: 'momo-001',
    status: 'failed',
    security: 'WPA3',
    signal: -70,
  },
  {
    id: 'hs-005',
    ssid: 'Office_5G',
    bssid: 'AA:BB:CC:DD:EE:05',
    capturedAt: new Date(Date.now() - 1800000).toISOString(),
    capturedBy: 'momo-001',
    status: 'cracked',
    password: 'office123',
    security: 'WPA2',
    signal: -48,
  },
];

export function Captures() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [revealedPasswords, setRevealedPasswords] = useState<Set<string>>(
    new Set()
  );

  const togglePassword = (id: string) => {
    const newSet = new Set(revealedPasswords);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setRevealedPasswords(newSet);
  };

  const filteredHandshakes = mockHandshakes.filter((hs) => {
    const matchesSearch = hs.ssid
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || hs.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const crackedCount = mockHandshakes.filter((h) => h.status === 'cracked').length;
  const pendingCount = mockHandshakes.filter((h) => h.status === 'pending').length;
  const crackingCount = mockHandshakes.filter((h) => h.status === 'cracking').length;

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex flex-wrap gap-4">
        <div className="badge-online">
          🔓 {crackedCount} Cracked
        </div>
        <div className="badge-info">
          ⏳ {crackingCount} Cracking
        </div>
        <div className="badge-pending">
          📋 {pendingCount} Pending
        </div>
        <div className="badge">
          {mockHandshakes.length} Total
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            placeholder="Search by SSID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-nexus-surface border border-border-default rounded-lg 
                       text-text-primary placeholder-text-muted focus:outline-none focus:border-neon-cyan"
          />
        </div>

        {/* Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="pl-10 pr-8 py-2 bg-nexus-surface border border-border-default rounded-lg 
                       text-text-primary appearance-none cursor-pointer focus:outline-none focus:border-neon-cyan"
          >
            <option value="all">All Status</option>
            <option value="cracked">Cracked</option>
            <option value="cracking">Cracking</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {/* Actions */}
        <button className="btn-primary flex items-center gap-2">
          <Send className="w-4 h-4" />
          Submit Selected
        </button>
        <button className="btn-secondary flex items-center gap-2">
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {/* Table */}
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>SSID</th>
              <th>BSSID</th>
              <th>Security</th>
              <th>Signal</th>
              <th>Status</th>
              <th>Password</th>
              <th>Captured</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredHandshakes.map((hs) => (
              <tr key={hs.id}>
                <td className="font-mono font-semibold">{hs.ssid}</td>
                <td className="font-mono text-text-muted text-xs">{hs.bssid}</td>
                <td>
                  <span
                    className={cn(
                      'badge',
                      hs.security === 'WPA3' ? 'badge-warning' : 'badge-info'
                    )}
                  >
                    {hs.security}
                  </span>
                </td>
                <td>
                  <span
                    className={cn(
                      'font-mono',
                      hs.signal && hs.signal > -50
                        ? 'text-neon-green'
                        : hs.signal && hs.signal > -70
                        ? 'text-neon-orange'
                        : 'text-neon-red'
                    )}
                  >
                    {hs.signal}dBm
                  </span>
                </td>
                <td>
                  <span
                    className={cn(
                      'badge',
                      hs.status === 'cracked' && 'badge-online',
                      hs.status === 'cracking' && 'badge-info',
                      hs.status === 'pending' && 'badge-pending',
                      hs.status === 'failed' && 'badge-offline'
                    )}
                  >
                    {hs.status}
                  </span>
                </td>
                <td>
                  {hs.password ? (
                    <div className="flex items-center gap-2">
                      <code className="font-mono text-neon-green">
                        {revealedPasswords.has(hs.id)
                          ? hs.password
                          : '••••••••'}
                      </code>
                      <button
                        onClick={() => togglePassword(hs.id)}
                        className="btn-icon p-1"
                      >
                        {revealedPasswords.has(hs.id) ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  ) : (
                    <span className="text-text-muted">-</span>
                  )}
                </td>
                <td className="text-text-muted text-sm">
                  {new Date(hs.capturedAt).toLocaleTimeString()}
                </td>
                <td>
                  {hs.status === 'pending' && (
                    <button className="btn-primary text-xs px-2 py-1">
                      Crack
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredHandshakes.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-text-muted">No captures found</p>
        </div>
      )}
    </div>
  );
}


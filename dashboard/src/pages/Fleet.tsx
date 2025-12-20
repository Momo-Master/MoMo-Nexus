import { useState } from 'react';
import { Search, Filter, Grid, List, RefreshCw } from 'lucide-react';
import { DeviceCard } from '../components/ui/DeviceCard';
import { cn } from '../lib/utils';
import type { Device } from '../types';

// Mock data
const mockDevices: Device[] = [
  {
    id: 'momo-001',
    name: 'MoMo-Alpha',
    type: 'momo',
    status: 'online',
    lastSeen: new Date(Date.now() - 30000).toISOString(),
    battery: 78,
    temperature: 52,
    location: { lat: 41.0082, lon: 28.9784 },
    stats: { captures: 23, uptime: 14400 },
    channel: 'wifi',
  },
  {
    id: 'momo-002',
    name: 'MoMo-Bravo',
    type: 'momo',
    status: 'degraded',
    lastSeen: new Date(Date.now() - 60000).toISOString(),
    battery: 34,
    temperature: 68,
    location: { lat: 41.0122, lon: 28.9754 },
    stats: { captures: 15, uptime: 7200 },
    channel: 'lora',
  },
  {
    id: 'ghost-001',
    name: 'Ghost-HQ',
    type: 'ghostbridge',
    status: 'online',
    lastSeen: new Date(Date.now() - 120000).toISOString(),
    temperature: 45,
    stats: { captures: 0, uptime: 86400 },
    channel: 'cellular',
  },
  {
    id: 'ghost-002',
    name: 'Ghost-Office',
    type: 'ghostbridge',
    status: 'online',
    lastSeen: new Date(Date.now() - 180000).toISOString(),
    temperature: 48,
    stats: { captures: 0, uptime: 172800 },
    channel: 'wifi',
  },
  {
    id: 'mimic-001',
    name: 'Mimic-USB-01',
    type: 'mimic',
    status: 'offline',
    lastSeen: new Date(Date.now() - 3600000).toISOString(),
    stats: { captures: 5, uptime: 0 },
    channel: 'wifi',
  },
];

export function Fleet() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredDevices = mockDevices.filter((device) => {
    const matchesSearch = device.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' || device.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const onlineCount = mockDevices.filter((d) => d.status === 'online').length;
  const offlineCount = mockDevices.filter((d) => d.status === 'offline').length;

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex flex-wrap gap-4">
        <div className="badge-online">
          <span className="w-2 h-2 rounded-full bg-neon-green" />
          {onlineCount} Online
        </div>
        <div className="badge-offline">
          <span className="w-2 h-2 rounded-full bg-neon-red" />
          {offlineCount} Offline
        </div>
        <div className="badge-info">
          {mockDevices.length} Total Devices
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            placeholder="Search devices..."
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
            <option value="online">Online</option>
            <option value="offline">Offline</option>
            <option value="degraded">Degraded</option>
          </select>
        </div>

        {/* View Toggle */}
        <div className="flex gap-1 p-1 bg-nexus-surface border border-border-default rounded-lg">
          <button
            onClick={() => setViewMode('grid')}
            className={cn(
              'p-2 rounded',
              viewMode === 'grid'
                ? 'bg-neon-green/10 text-neon-green'
                : 'text-text-secondary hover:text-text-primary'
            )}
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={cn(
              'p-2 rounded',
              viewMode === 'list'
                ? 'bg-neon-green/10 text-neon-green'
                : 'text-text-secondary hover:text-text-primary'
            )}
          >
            <List className="w-4 h-4" />
          </button>
        </div>

        {/* Refresh */}
        <button className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Device Grid/List */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredDevices.map((device) => (
            <DeviceCard key={device.id} device={device} />
          ))}
        </div>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Device</th>
                <th>Type</th>
                <th>Status</th>
                <th>Channel</th>
                <th>Battery</th>
                <th>Captures</th>
                <th>Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {filteredDevices.map((device) => (
                <tr key={device.id}>
                  <td className="font-mono">{device.name}</td>
                  <td className="capitalize">{device.type}</td>
                  <td>
                    <span
                      className={cn(
                        'badge',
                        device.status === 'online' && 'badge-online',
                        device.status === 'offline' && 'badge-offline',
                        device.status === 'degraded' && 'badge-warning'
                      )}
                    >
                      {device.status}
                    </span>
                  </td>
                  <td className="capitalize">{device.channel}</td>
                  <td>{device.battery ? `${device.battery}%` : '-'}</td>
                  <td className="font-mono text-neon-green">
                    {device.stats.captures}
                  </td>
                  <td className="text-text-muted text-sm">
                    {new Date(device.lastSeen).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filteredDevices.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-text-muted">No devices found</p>
        </div>
      )}
    </div>
  );
}


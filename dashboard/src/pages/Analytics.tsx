import { useState } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  TrendingUp,
  Calendar,
  Download,
  Filter,
} from 'lucide-react';
import { cn } from '../lib/utils';

// Mock data for charts
const capturesByDay = [
  { date: 'Mon', handshakes: 12, pmkid: 5, credentials: 2 },
  { date: 'Tue', handshakes: 19, pmkid: 8, credentials: 4 },
  { date: 'Wed', handshakes: 8, pmkid: 3, credentials: 1 },
  { date: 'Thu', handshakes: 25, pmkid: 12, credentials: 6 },
  { date: 'Fri', handshakes: 32, pmkid: 15, credentials: 8 },
  { date: 'Sat', handshakes: 28, pmkid: 10, credentials: 5 },
  { date: 'Sun', handshakes: 15, pmkid: 7, credentials: 3 },
];

const crackRateData = [
  { date: 'Week 1', success: 45, failed: 12 },
  { date: 'Week 2', success: 52, failed: 8 },
  { date: 'Week 3', success: 38, failed: 15 },
  { date: 'Week 4', success: 67, failed: 10 },
];

const securityDistribution = [
  { name: 'WPA2', value: 65, color: '#00ff88' },
  { name: 'WPA3', value: 20, color: '#00d4ff' },
  { name: 'WPA', value: 10, color: '#ff8800' },
  { name: 'WEP', value: 5, color: '#ff4444' },
];

const channelUsage = [
  { name: 'WiFi', value: 45, color: '#00ff88' },
  { name: 'LoRa', value: 30, color: '#00d4ff' },
  { name: '4G/LTE', value: 20, color: '#ff00ff' },
  { name: 'BLE', value: 5, color: '#ff8800' },
];

const topNetworks = [
  { ssid: 'CORP-WiFi-5G', captures: 23, cracked: true },
  { ssid: 'HomeNetwork', captures: 18, cracked: true },
  { ssid: 'GuestNetwork', captures: 15, cracked: false },
  { ssid: 'Starbucks_Free', captures: 12, cracked: true },
  { ssid: 'Airport_WiFi', captures: 10, cracked: false },
];

const devicePerformance = [
  { device: 'MoMo-Alpha', captures: 47, uptime: 98.5 },
  { device: 'MoMo-Bravo', captures: 32, uptime: 95.2 },
  { device: 'Ghost-HQ', captures: 0, uptime: 99.9 },
  { device: 'Mimic-USB', captures: 8, uptime: 45.0 },
];

type TimeRange = '7d' | '30d' | '90d' | 'all';

export function Analytics() {
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex gap-1 p-1 bg-nexus-surface border border-border-default rounded-lg">
            {(['7d', '30d', '90d', 'all'] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={cn(
                  'px-3 py-1.5 rounded text-sm font-medium transition-all',
                  timeRange === range
                    ? 'bg-neon-green/10 text-neon-green'
                    : 'text-text-secondary hover:text-text-primary'
                )}
              >
                {range === 'all' ? 'All Time' : range}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2">
          <button className="btn-secondary flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filter
          </button>
          <button className="btn-primary flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export Report
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-neon-green" />
            <span className="text-xs text-text-muted">Total Captures</span>
          </div>
          <p className="text-2xl font-mono font-bold text-neon-green">139</p>
          <p className="text-xs text-neon-green mt-1">↑ 23% vs last week</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-neon-magenta" />
            <span className="text-xs text-text-muted">Crack Rate</span>
          </div>
          <p className="text-2xl font-mono font-bold text-neon-magenta">78%</p>
          <p className="text-xs text-neon-green mt-1">↑ 5% vs last week</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="w-4 h-4 text-neon-cyan" />
            <span className="text-xs text-text-muted">Avg Daily</span>
          </div>
          <p className="text-2xl font-mono font-bold text-neon-cyan">19.8</p>
          <p className="text-xs text-text-muted mt-1">captures/day</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-neon-orange" />
            <span className="text-xs text-text-muted">Credentials</span>
          </div>
          <p className="text-2xl font-mono font-bold text-neon-orange">29</p>
          <p className="text-xs text-neon-green mt-1">↑ 12% vs last week</p>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Captures Over Time */}
        <div className="card">
          <h3 className="font-mono font-semibold text-text-primary mb-4">
            Captures Over Time
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={capturesByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                <XAxis dataKey="date" stroke="#8888aa" fontSize={12} />
                <YAxis stroke="#8888aa" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#12121a',
                    border: '1px solid #2a2a3a',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
                <Bar dataKey="handshakes" fill="#00ff88" name="Handshakes" />
                <Bar dataKey="pmkid" fill="#00d4ff" name="PMKID" />
                <Bar dataKey="credentials" fill="#ff00ff" name="Credentials" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Crack Success Rate */}
        <div className="card">
          <h3 className="font-mono font-semibold text-text-primary mb-4">
            Crack Success Rate
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={crackRateData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                <XAxis dataKey="date" stroke="#8888aa" fontSize={12} />
                <YAxis stroke="#8888aa" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#12121a',
                    border: '1px solid #2a2a3a',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="success"
                  stroke="#00ff88"
                  strokeWidth={2}
                  dot={{ fill: '#00ff88' }}
                  name="Cracked"
                />
                <Line
                  type="monotone"
                  dataKey="failed"
                  stroke="#ff4444"
                  strokeWidth={2}
                  dot={{ fill: '#ff4444' }}
                  name="Failed"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Security Distribution */}
        <div className="card">
          <h3 className="font-mono font-semibold text-text-primary mb-4">
            Security Types
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={securityDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {securityDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#12121a',
                    border: '1px solid #2a2a3a',
                    borderRadius: '8px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-2">
            {securityDistribution.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-xs text-text-secondary">
                  {item.name} ({item.value}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Channel Usage */}
        <div className="card">
          <h3 className="font-mono font-semibold text-text-primary mb-4">
            Channel Usage
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={channelUsage}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {channelUsage.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#12121a',
                    border: '1px solid #2a2a3a',
                    borderRadius: '8px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-2">
            {channelUsage.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-xs text-text-secondary">
                  {item.name} ({item.value}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Top Networks */}
        <div className="card">
          <h3 className="font-mono font-semibold text-text-primary mb-4">
            Top Networks
          </h3>
          <div className="space-y-3">
            {topNetworks.map((network, i) => (
              <div
                key={network.ssid}
                className="flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs text-text-muted font-mono w-4">
                    #{i + 1}
                  </span>
                  <span className="font-mono text-sm truncate max-w-[120px]">
                    {network.ssid}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-neon-cyan font-mono">
                    {network.captures}
                  </span>
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full',
                      network.cracked ? 'bg-neon-green' : 'bg-text-muted'
                    )}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Device Performance */}
      <div className="card">
        <h3 className="font-mono font-semibold text-text-primary mb-4">
          Device Performance
        </h3>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Device</th>
                <th>Captures</th>
                <th>Uptime</th>
                <th>Performance</th>
              </tr>
            </thead>
            <tbody>
              {devicePerformance.map((device) => (
                <tr key={device.device}>
                  <td className="font-mono">{device.device}</td>
                  <td className="font-mono text-neon-green">{device.captures}</td>
                  <td
                    className={cn(
                      'font-mono',
                      device.uptime > 90
                        ? 'text-neon-green'
                        : device.uptime > 70
                        ? 'text-neon-orange'
                        : 'text-neon-red'
                    )}
                  >
                    {device.uptime}%
                  </td>
                  <td>
                    <div className="w-full bg-nexus-bg rounded-full h-2">
                      <div
                        className={cn(
                          'h-2 rounded-full',
                          device.uptime > 90
                            ? 'bg-neon-green'
                            : device.uptime > 70
                            ? 'bg-neon-orange'
                            : 'bg-neon-red'
                        )}
                        style={{ width: `${device.uptime}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}


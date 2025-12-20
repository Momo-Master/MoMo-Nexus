import { useState } from 'react';
import {
  Fish,
  Globe,
  User,
  Key,
  Cookie,
  Clock,
  ExternalLink,
  Copy,
  Eye,
  EyeOff,
  Power,
  PowerOff,
  RefreshCw,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { formatRelativeTime } from '../lib/utils';

interface Phishlet {
  id: string;
  name: string;
  hostname: string;
  enabled: boolean;
  sessions: number;
  lastHit?: string;
}

interface Session {
  id: string;
  phishlet: string;
  username: string;
  password: string;
  tokens: { name: string; value: string }[];
  userAgent: string;
  remoteAddr: string;
  createdAt: string;
}

// Mock data
const mockPhishlets: Phishlet[] = [
  {
    id: 'ph-001',
    name: 'microsoft365',
    hostname: 'login.ms-secure.com',
    enabled: true,
    sessions: 5,
    lastHit: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'ph-002',
    name: 'google',
    hostname: 'accounts.g-secure.com',
    enabled: true,
    sessions: 3,
    lastHit: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'ph-003',
    name: 'linkedin',
    hostname: 'www.li-secure.com',
    enabled: false,
    sessions: 0,
  },
  {
    id: 'ph-004',
    name: 'okta',
    hostname: 'login.okta-secure.com',
    enabled: true,
    sessions: 2,
    lastHit: new Date(Date.now() - 86400000).toISOString(),
  },
];

const mockSessions: Session[] = [
  {
    id: 'sess-001',
    phishlet: 'microsoft365',
    username: 'john.doe@company.com',
    password: 'Summer2024!',
    tokens: [
      { name: 'ESTSAUTH', value: 'eyJ0eXAiOi...' },
      { name: 'ESTSAUTHPERSISTENT', value: 'eyJ0eXAiOi...' },
    ],
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    remoteAddr: '192.168.1.105',
    createdAt: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'sess-002',
    phishlet: 'google',
    username: 'admin@corp.com',
    password: 'P@ssw0rd123',
    tokens: [
      { name: 'SID', value: 'SIDABC123...' },
      { name: 'HSID', value: 'HSIDXYZ789...' },
    ],
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X)',
    remoteAddr: '10.0.0.55',
    createdAt: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'sess-003',
    phishlet: 'microsoft365',
    username: 'cfo@company.com',
    password: 'Finance2024#',
    tokens: [
      { name: 'ESTSAUTH', value: 'eyJ0eXAiOi...' },
    ],
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS)',
    remoteAddr: '172.16.0.10',
    createdAt: new Date(Date.now() - 10800000).toISOString(),
  },
];

export function Phishing() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [revealedPasswords, setRevealedPasswords] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const togglePassword = (id: string) => {
    const newSet = new Set(revealedPasswords);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setRevealedPasswords(newSet);
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const activePhishlets = mockPhishlets.filter((p) => p.enabled).length;
  const totalSessions = mockSessions.length;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-magenta/10 border border-neon-magenta/30 flex items-center justify-center">
            <Fish className="w-6 h-6 text-neon-magenta" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-magenta">
              {activePhishlets}
            </p>
            <p className="text-sm text-text-muted">Active Phishlets</p>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-green/10 border border-neon-green/30 flex items-center justify-center">
            <User className="w-6 h-6 text-neon-green" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-green">
              {totalSessions}
            </p>
            <p className="text-sm text-text-muted">Sessions Captured</p>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center">
            <Cookie className="w-6 h-6 text-neon-cyan" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-cyan">
              {mockSessions.reduce((acc, s) => acc + s.tokens.length, 0)}
            </p>
            <p className="text-sm text-text-muted">Tokens Harvested</p>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-orange/10 border border-neon-orange/30 flex items-center justify-center">
            <Globe className="w-6 h-6 text-neon-orange" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-orange">
              {mockPhishlets.length}
            </p>
            <p className="text-sm text-text-muted">Phishlets</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Phishlets */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-mono font-semibold text-text-primary">Phishlets</h3>
            <button className="btn-icon">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-3">
            {mockPhishlets.map((phishlet) => (
              <div
                key={phishlet.id}
                className="p-3 bg-nexus-elevated rounded-lg border border-border-default"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Fish
                      className={cn(
                        'w-4 h-4',
                        phishlet.enabled ? 'text-neon-magenta' : 'text-text-muted'
                      )}
                    />
                    <span className="font-mono font-semibold">{phishlet.name}</span>
                  </div>
                  <button
                    className={cn(
                      'p-1.5 rounded',
                      phishlet.enabled
                        ? 'bg-neon-green/10 text-neon-green'
                        : 'bg-neon-red/10 text-neon-red'
                    )}
                  >
                    {phishlet.enabled ? (
                      <Power className="w-4 h-4" />
                    ) : (
                      <PowerOff className="w-4 h-4" />
                    )}
                  </button>
                </div>
                <p className="text-xs text-text-muted mb-2 font-mono">
                  {phishlet.hostname}
                </p>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-neon-cyan">{phishlet.sessions} sessions</span>
                  {phishlet.lastHit && (
                    <span className="text-text-muted">
                      {formatRelativeTime(phishlet.lastHit)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sessions List */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-mono font-semibold text-text-primary">
              Captured Sessions
            </h3>
            <span className="text-xs text-text-muted">{totalSessions} total</span>
          </div>

          <div className="space-y-3">
            {mockSessions.map((session) => (
              <div
                key={session.id}
                className={cn(
                  'p-4 rounded-lg border cursor-pointer transition-all',
                  selectedSession?.id === session.id
                    ? 'bg-neon-magenta/10 border-neon-magenta/30'
                    : 'bg-nexus-elevated border-border-default hover:border-neon-magenta/20'
                )}
                onClick={() => setSelectedSession(session)}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="badge-info">{session.phishlet}</span>
                      <span className="text-xs text-text-muted">
                        {formatRelativeTime(session.createdAt)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <User className="w-4 h-4 text-neon-cyan" />
                      <span className="font-mono text-sm">{session.username}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4 text-neon-green" />
                      <code className="font-mono text-sm text-neon-green">
                        {revealedPasswords.has(session.id)
                          ? session.password
                          : '••••••••'}
                      </code>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          togglePassword(session.id);
                        }}
                        className="btn-icon p-1"
                      >
                        {revealedPasswords.has(session.id) ? (
                          <EyeOff className="w-3 h-3" />
                        ) : (
                          <Eye className="w-3 h-3" />
                        )}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(session.password, `pass-${session.id}`);
                        }}
                        className="btn-icon p-1"
                      >
                        <Copy
                          className={cn(
                            'w-3 h-3',
                            copiedId === `pass-${session.id}` && 'text-neon-green'
                          )}
                        />
                      </button>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-text-muted">{session.remoteAddr}</p>
                    <p className="text-xs text-neon-cyan mt-1">
                      {session.tokens.length} tokens
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Session Details Modal */}
      {selectedSession && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-mono font-semibold text-text-primary">
              Session Details
            </h3>
            <button
              onClick={() => setSelectedSession(null)}
              className="text-text-muted hover:text-text-primary"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-text-muted mb-1">Username</p>
              <code className="font-mono text-neon-cyan">{selectedSession.username}</code>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-1">Password</p>
              <code className="font-mono text-neon-green">{selectedSession.password}</code>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-1">Remote IP</p>
              <code className="font-mono">{selectedSession.remoteAddr}</code>
            </div>
            <div>
              <p className="text-xs text-text-muted mb-1">Phishlet</p>
              <code className="font-mono">{selectedSession.phishlet}</code>
            </div>
          </div>

          <div className="mb-4">
            <p className="text-xs text-text-muted mb-1">User Agent</p>
            <code className="font-mono text-xs text-text-secondary break-all">
              {selectedSession.userAgent}
            </code>
          </div>

          <div>
            <p className="text-xs text-text-muted mb-2">
              Tokens ({selectedSession.tokens.length})
            </p>
            <div className="terminal max-h-48 overflow-y-auto">
              {selectedSession.tokens.map((token, i) => (
                <div key={i} className="flex items-center justify-between py-1">
                  <span className="text-neon-magenta">{token.name}:</span>
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-text-secondary truncate max-w-[200px]">
                      {token.value}
                    </code>
                    <button
                      onClick={() => copyToClipboard(token.value, `token-${i}`)}
                      className="btn-icon p-1"
                    >
                      <Copy
                        className={cn(
                          'w-3 h-3',
                          copiedId === `token-${i}` && 'text-neon-green'
                        )}
                      />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-2 mt-4">
            <button className="btn-primary flex items-center gap-2">
              <ExternalLink className="w-4 h-4" />
              Open in Browser
            </button>
            <button className="btn-secondary flex items-center gap-2">
              <Copy className="w-4 h-4" />
              Export Session
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


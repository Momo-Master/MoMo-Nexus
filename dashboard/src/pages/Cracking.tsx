import { Cpu, Clock, Zap, CheckCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import type { CrackJob } from '../types';

// Mock data
const mockJobs: CrackJob[] = [
  {
    id: 'job-001',
    handshakeId: 'hs-002',
    ssid: 'HomeNetwork_2G',
    status: 'cracking',
    progress: 67,
    startedAt: new Date(Date.now() - 1800000).toISOString(),
    hashRate: 125000,
    wordlist: 'rockyou.txt',
  },
  {
    id: 'job-002',
    handshakeId: 'hs-006',
    ssid: 'Cafe_Guest_5G',
    status: 'cracking',
    progress: 23,
    startedAt: new Date(Date.now() - 600000).toISOString(),
    hashRate: 118000,
    wordlist: 'custom-wifi.txt',
  },
  {
    id: 'job-003',
    handshakeId: 'hs-001',
    ssid: 'CORP-WiFi-5G',
    status: 'cracked',
    progress: 100,
    startedAt: new Date(Date.now() - 3600000).toISOString(),
    completedAt: new Date(Date.now() - 3000000).toISOString(),
    password: 'corporate2024!',
    hashRate: 0,
    wordlist: 'rockyou.txt',
  },
];

export function Cracking() {
  const activeJobs = mockJobs.filter((j) => j.status === 'cracking');
  const completedJobs = mockJobs.filter((j) => j.status === 'cracked');

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center">
            <Cpu className="w-6 h-6 text-neon-cyan" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-cyan">
              {activeJobs.length}
            </p>
            <p className="text-sm text-text-muted">Active Jobs</p>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-green/10 border border-neon-green/30 flex items-center justify-center">
            <CheckCircle className="w-6 h-6 text-neon-green" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-green">
              {completedJobs.length}
            </p>
            <p className="text-sm text-text-muted">Cracked Today</p>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-magenta/10 border border-neon-magenta/30 flex items-center justify-center">
            <Zap className="w-6 h-6 text-neon-magenta" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-magenta">
              125K
            </p>
            <p className="text-sm text-text-muted">Hash/sec</p>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-neon-orange/10 border border-neon-orange/30 flex items-center justify-center">
            <Clock className="w-6 h-6 text-neon-orange" />
          </div>
          <div>
            <p className="text-2xl font-mono font-bold text-neon-orange">
              ~2h
            </p>
            <p className="text-sm text-text-muted">Avg Time</p>
          </div>
        </div>
      </div>

      {/* Active Jobs */}
      <div className="card">
        <h3 className="font-mono font-semibold text-text-primary mb-4">
          Active Jobs
        </h3>
        <div className="space-y-4">
          {activeJobs.length > 0 ? (
            activeJobs.map((job) => (
              <div
                key={job.id}
                className="p-4 bg-nexus-elevated rounded-lg border border-border-default"
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="font-mono font-semibold text-text-primary">
                      {job.ssid}
                    </h4>
                    <p className="text-xs text-text-muted">
                      Wordlist: {job.wordlist}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-neon-cyan">
                      {job.hashRate?.toLocaleString()} H/s
                    </p>
                    <p className="text-xs text-text-muted">
                      Started {new Date(job.startedAt).toLocaleTimeString()}
                    </p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="relative h-3 bg-nexus-bg rounded-full overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-neon-cyan to-neon-green rounded-full transition-all duration-500"
                    style={{ width: `${job.progress}%` }}
                  />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xs font-mono text-text-primary">
                      {job.progress}%
                    </span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-text-muted">
              No active cracking jobs
            </div>
          )}
        </div>
      </div>

      {/* Completed Jobs */}
      <div className="card">
        <h3 className="font-mono font-semibold text-text-primary mb-4">
          Completed Today
        </h3>
        <div className="space-y-2">
          {completedJobs.map((job) => (
            <div
              key={job.id}
              className="flex items-center justify-between p-3 bg-nexus-elevated rounded-lg"
            >
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-neon-green" />
                <div>
                  <p className="font-mono font-semibold">{job.ssid}</p>
                  <p className="text-xs text-text-muted">
                    {job.wordlist}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <code className="font-mono text-neon-green">{job.password}</code>
                <p className="text-xs text-text-muted">
                  {new Date(job.completedAt!).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* GPU Status */}
      <div className="card">
        <h3 className="font-mono font-semibold text-text-primary mb-4">
          Cloud GPU Status
        </h3>
        <div className="terminal">
          <div className="terminal-header">
            <div className="terminal-dot bg-neon-red" />
            <div className="terminal-dot bg-neon-orange" />
            <div className="terminal-dot bg-neon-green" />
            <span className="text-xs text-text-muted ml-2">hashcat-cloud.vps</span>
          </div>
          <pre className="text-neon-green text-sm">
{`Session..........: hashcat
Status...........: Running
Hash.Mode........: 22000 (WPA-PBKDF2-PMKID+EAPOL)
Speed.#1.........: 125.4 kH/s
Recovered........: 1/3 (33.33%)
Progress.........: 8388608/14344384 (58.48%)
Time.Started.....: Sat Dec 20 14:32:00 2025
Time.Estimated...: Sat Dec 20 15:45:12 2025`}
          </pre>
        </div>
      </div>
    </div>
  );
}


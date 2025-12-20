import { Toaster, toast } from 'react-hot-toast';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

// Toast provider component
export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#12121a',
          color: '#e0e0e0',
          border: '1px solid #2a2a3a',
          borderRadius: '8px',
          padding: '12px 16px',
          fontSize: '14px',
          fontFamily: 'Inter, system-ui, sans-serif',
        },
      }}
    />
  );
}

// Custom toast functions
export const nexusToast = {
  success: (message: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-green/30 rounded-lg p-4 shadow-neon-green max-w-md`}
      >
        <CheckCircle className="w-5 h-5 text-neon-green flex-shrink-0" />
        <p className="flex-1 text-text-primary">{message}</p>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ));
  },

  error: (message: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-red/30 rounded-lg p-4 shadow-neon-red max-w-md`}
      >
        <XCircle className="w-5 h-5 text-neon-red flex-shrink-0" />
        <p className="flex-1 text-text-primary">{message}</p>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ));
  },

  warning: (message: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-orange/30 rounded-lg p-4 max-w-md`}
      >
        <AlertTriangle className="w-5 h-5 text-neon-orange flex-shrink-0" />
        <p className="flex-1 text-text-primary">{message}</p>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ));
  },

  info: (message: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-cyan/30 rounded-lg p-4 max-w-md`}
      >
        <Info className="w-5 h-5 text-neon-cyan flex-shrink-0" />
        <p className="flex-1 text-text-primary">{message}</p>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ));
  },

  // Special toasts for Nexus events
  handshakeCaptured: (ssid: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-green/30 rounded-lg p-4 shadow-neon-green max-w-md`}
      >
        <span className="text-xl">🤝</span>
        <div className="flex-1">
          <p className="text-neon-green font-semibold">Handshake Captured!</p>
          <p className="text-text-secondary text-sm font-mono">{ssid}</p>
        </div>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ), { duration: 6000 });
  },

  passwordCracked: (ssid: string, password: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-magenta/30 rounded-lg p-4 shadow-neon-magenta max-w-md`}
      >
        <span className="text-xl">🔓</span>
        <div className="flex-1">
          <p className="text-neon-magenta font-semibold">Password Cracked!</p>
          <p className="text-text-secondary text-sm">
            <span className="font-mono">{ssid}</span>: 
            <code className="text-neon-green ml-1">{password}</code>
          </p>
        </div>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ), { duration: 8000 });
  },

  deviceOnline: (deviceName: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-cyan/30 rounded-lg p-4 max-w-md`}
      >
        <span className="text-xl">📡</span>
        <div className="flex-1">
          <p className="text-neon-cyan font-semibold">Device Online</p>
          <p className="text-text-secondary text-sm font-mono">{deviceName}</p>
        </div>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ));
  },

  deviceOffline: (deviceName: string) => {
    toast.custom((t) => (
      <div
        className={`${
          t.visible ? 'animate-enter' : 'animate-leave'
        } flex items-center gap-3 bg-nexus-surface border border-neon-red/30 rounded-lg p-4 max-w-md`}
      >
        <span className="text-xl">📴</span>
        <div className="flex-1">
          <p className="text-neon-red font-semibold">Device Offline</p>
          <p className="text-text-secondary text-sm font-mono">{deviceName}</p>
        </div>
        <button
          onClick={() => toast.dismiss(t.id)}
          className="text-text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ));
  },
};

// Re-export original toast for simple cases
export { toast };


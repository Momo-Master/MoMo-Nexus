import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts(customShortcuts?: ShortcutConfig[]) {
  const navigate = useNavigate();

  // Default navigation shortcuts
  const defaultShortcuts: ShortcutConfig[] = [
    { key: 'h', ctrl: true, action: () => navigate('/'), description: 'Go to Dashboard' },
    { key: 'f', ctrl: true, action: () => navigate('/fleet'), description: 'Go to Fleet' },
    { key: 'c', ctrl: true, shift: true, action: () => navigate('/captures'), description: 'Go to Captures' },
    { key: 'k', ctrl: true, action: () => navigate('/cracking'), description: 'Go to Cracking' },
    { key: 'a', ctrl: true, shift: true, action: () => navigate('/analytics'), description: 'Go to Analytics' },
    { key: 's', ctrl: true, shift: true, action: () => navigate('/settings'), description: 'Go to Settings' },
    { key: '/', ctrl: true, action: () => {
      // Focus search input if exists
      const searchInput = document.querySelector<HTMLInputElement>('[data-search-input]');
      searchInput?.focus();
    }, description: 'Focus search' },
    { key: 'Escape', action: () => {
      // Close any open modal
      const closeButton = document.querySelector<HTMLButtonElement>('[data-modal-close]');
      closeButton?.click();
    }, description: 'Close modal' },
  ];

  const allShortcuts = [...defaultShortcuts, ...(customShortcuts || [])];

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Ignore if typing in input/textarea
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
      // Allow Escape to still work
      if (e.key !== 'Escape') return;
    }

    for (const shortcut of allShortcuts) {
      const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey);
      const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey;
      const altMatch = shortcut.alt ? e.altKey : !e.altKey;
      const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();

      if (ctrlMatch && shiftMatch && altMatch && keyMatch) {
        e.preventDefault();
        shortcut.action();
        return;
      }
    }
  }, [allShortcuts]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return { shortcuts: allShortcuts };
}

// Hook to show keyboard shortcuts modal
export function useShortcutsModal() {
  const { shortcuts } = useKeyboardShortcuts();

  const formatKey = (shortcut: ShortcutConfig) => {
    const keys: string[] = [];
    if (shortcut.ctrl) keys.push('Ctrl');
    if (shortcut.shift) keys.push('Shift');
    if (shortcut.alt) keys.push('Alt');
    keys.push(shortcut.key.toUpperCase());
    return keys.join(' + ');
  };

  return { shortcuts, formatKey };
}

// Component to display shortcuts
export function KeyboardShortcutsList() {
  const { shortcuts, formatKey } = useShortcutsModal();

  const groupedShortcuts = {
    navigation: shortcuts.filter((s) => s.description.startsWith('Go to')),
    actions: shortcuts.filter((s) => !s.description.startsWith('Go to')),
  };

  return (
    <div className="space-y-6">
      <div>
        <h4 className="font-mono text-sm text-text-muted mb-3">Navigation</h4>
        <div className="space-y-2">
          {groupedShortcuts.navigation.map((shortcut, i) => (
            <div key={i} className="flex items-center justify-between">
              <span className="text-text-secondary">{shortcut.description}</span>
              <kbd className="px-2 py-1 bg-nexus-elevated rounded text-xs font-mono text-neon-cyan">
                {formatKey(shortcut)}
              </kbd>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h4 className="font-mono text-sm text-text-muted mb-3">Actions</h4>
        <div className="space-y-2">
          {groupedShortcuts.actions.map((shortcut, i) => (
            <div key={i} className="flex items-center justify-between">
              <span className="text-text-secondary">{shortcut.description}</span>
              <kbd className="px-2 py-1 bg-nexus-elevated rounded text-xs font-mono text-neon-cyan">
                {formatKey(shortcut)}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


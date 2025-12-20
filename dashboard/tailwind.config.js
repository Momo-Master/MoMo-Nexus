/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        'nexus-bg': '#0a0a0f',
        'nexus-surface': '#12121a',
        'nexus-elevated': '#1a1a24',
        'nexus-tertiary': '#24242e',
        'nexus-hover': '#22222e',
        
        // Neon Colors
        'neon-green': '#00ff88',
        'neon-cyan': '#00d4ff',
        'neon-magenta': '#ff00ff',
        'neon-orange': '#ff8800',
        'neon-red': '#ff4444',
        'neon-yellow': '#ffff00',
        
        // Text
        'text-primary': '#e0e0e0',
        'text-secondary': '#8888aa',
        'text-muted': '#555566',
        
        // Borders
        'border-default': '#2a2a3a',
        'border-active': '#3a3a4a',
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'neon-green': '0 0 20px rgba(0, 255, 136, 0.3)',
        'neon-cyan': '0 0 20px rgba(0, 212, 255, 0.3)',
        'neon-magenta': '0 0 20px rgba(255, 0, 255, 0.3)',
        'neon-red': '0 0 20px rgba(255, 68, 68, 0.3)',
        'card': '0 4px 20px rgba(0, 0, 0, 0.5)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scan': 'scan 2s linear infinite',
      },
      keyframes: {
        glow: {
          '0%': { opacity: '0.5' },
          '100%': { opacity: '1' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid': '20px 20px',
      },
    },
  },
  plugins: [],
}


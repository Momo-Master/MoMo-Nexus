# 🌐 Nexus Dashboard

> Cyberpunk-themed control center for the MoMo Ecosystem

<p align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/Tailwind-3.4-38B2AC?style=for-the-badge&logo=tailwindcss" alt="Tailwind">
  <img src="https://img.shields.io/badge/Vite-7-646CFF?style=for-the-badge&logo=vite" alt="Vite">
</p>

---

## 🎨 Features

### Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Real-time stats, device fleet, activity feed, map |
| **Fleet** | Device management with grid/list view |
| **Captures** | Handshake table with password reveal |
| **Cracking** | Cloud GPU job queue with progress |
| **Phishing** | Evilginx sessions & phishlet control |
| **Analytics** | Charts, trends, device performance |
| **Settings** | Channels, cloud, security, appearance |

### UI Components

| Component | Description |
|-----------|-------------|
| **Device Map** | Leaflet + Stadia dark theme, device markers |
| **Toast Notifications** | Handshake, crack, device status alerts |
| **Skeleton Loading** | Placeholder UI during data fetch |
| **Mobile Navigation** | Bottom nav for responsive design |
| **Device Modal** | Detailed device info popup |
| **Theme Toggle** | Dark / Light / System mode |
| **Keyboard Shortcuts** | Ctrl+H, Ctrl+F, Escape, etc. |
| **Export Functions** | CSV / JSON data export |

---

## 🚀 Quick Start

```bash
# Install dependencies (use legacy-peer-deps for React 19 compatibility)
npm install --legacy-peer-deps

# Development server
npm run dev
# → http://localhost:5173/

# Build for production
npm run build
# → dist/ folder (~600KB gzipped)

# Preview production build
npm run preview
```

---

## 🎯 Design System

### Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Background | `#0a0a0f` | Main background |
| Surface | `#12121a` | Cards, panels |
| Neon Green | `#00ff88` | Primary, success |
| Neon Cyan | `#00d4ff` | Secondary, links |
| Neon Magenta | `#ff00ff` | Accent, phishing |
| Neon Orange | `#ff8800` | Warning |
| Neon Red | `#ff4444` | Error, offline |

### Typography

- **Headings**: JetBrains Mono (monospace)
- **Body**: Inter (sans-serif)
- **Code**: Fira Code (monospace)

---

## 📁 Project Structure

```
dashboard/
├── public/
│   └── nexus.svg           # Logo
├── src/
│   ├── components/
│   │   ├── layout/         # Layout, Sidebar, Header
│   │   └── ui/             # StatCard, ActivityFeed, DeviceCard
│   ├── hooks/              # useWebSocket, useApi
│   ├── lib/                # Utilities
│   ├── pages/              # All pages
│   ├── types/              # TypeScript types
│   ├── App.tsx             # Router
│   ├── main.tsx            # Entry point
│   └── index.css           # Tailwind + custom styles
├── tailwind.config.js      # Theme configuration
├── vite.config.ts          # Build configuration
└── package.json
```

---

## 🔌 API Integration

The dashboard connects to the Nexus FastAPI backend:

```typescript
// API base URL
const API_URL = 'http://localhost:8080/api/v1'

// WebSocket for real-time updates
const WS_URL = 'ws://localhost:8080/ws'
```

### Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fleet/devices` | GET | List all devices |
| `/captures/handshakes` | GET | List handshakes |
| `/cloud/hashcat/jobs` | GET | Crack job queue |
| `/cloud/evilginx/sessions` | GET | Phishing sessions |
| `/stats` | GET | Dashboard stats |

---

## 🖥️ Deployment on Pi 4

```bash
# Build optimized bundle
npm run build

# Serve with nginx
sudo cp -r dist/* /var/www/nexus-dashboard/

# Or serve with Node
npx serve dist -l 3000
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name nexus.local;
    root /var/www/nexus-dashboard;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8080;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 📱 Mobile Support

- Responsive design (works on tablet/phone)
- Touch-friendly buttons
- Collapsible sidebar
- Bottom navigation on mobile

---

## 🔧 Development

```bash
# Type checking
npm run lint

# Format code
npm run format
```

---

## 📄 License

MIT License - MoMo Ecosystem

---

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+H` | Go to Dashboard |
| `Ctrl+F` | Go to Fleet |
| `Ctrl+Shift+C` | Go to Captures |
| `Ctrl+K` | Go to Cracking |
| `Ctrl+Shift+A` | Go to Analytics |
| `Ctrl+Shift+S` | Go to Settings |
| `Ctrl+/` | Focus search |
| `Escape` | Close modal |

---

*Nexus Dashboard v1.1.0*

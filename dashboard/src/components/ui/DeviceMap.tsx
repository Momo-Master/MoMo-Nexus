import { useEffect, useState, useId } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { cn } from '../../lib/utils';
import type { Device } from '../../types';

// Fix for default marker icon issue in React-Leaflet
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom marker icons
const createIcon = (color: string) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        width: 24px;
        height: 24px;
        background: ${color};
        border: 2px solid #0a0a0f;
        border-radius: 50%;
        box-shadow: 0 0 10px ${color}80;
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="
          width: 8px;
          height: 8px;
          background: #0a0a0f;
          border-radius: 50%;
        "></div>
      </div>
    `,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
};

const deviceColors: Record<string, string> = {
  momo: '#00d4ff',
  ghostbridge: '#ff00ff',
  mimic: '#ff8800',
  nexus: '#00ff88',
};

const statusColors: Record<string, string> = {
  online: '#00ff88',
  offline: '#ff4444',
  degraded: '#ff8800',
};

interface DeviceMapProps {
  devices: Device[];
  center?: [number, number];
  zoom?: number;
  className?: string;
  onDeviceClick?: (device: Device) => void;
}

// Component to fit bounds when devices change
function FitBounds({ devices }: { devices: Device[] }) {
  const map = useMap();

  useEffect(() => {
    const validDevices = devices.filter((d) => d.location);
    if (validDevices.length > 0) {
      const bounds = L.latLngBounds(
        validDevices.map((d) => [d.location!.lat, d.location!.lon])
      );
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [devices, map]);

  return null;
}

export function DeviceMap({
  devices,
  center = [41.0082, 28.9784], // Istanbul default
  zoom = 12,
  className,
  onDeviceClick,
}: DeviceMapProps) {
  const mapId = useId();
  const [mapReady, setMapReady] = useState(false);
  const devicesWithLocation = devices.filter((d) => d.location);

  // Prevent double initialization in React 18 Strict Mode
  useEffect(() => {
    setMapReady(true);
    return () => setMapReady(false);
  }, []);

  if (!mapReady) {
    return (
      <div className={cn('rounded-lg overflow-hidden border border-border-default flex items-center justify-center bg-nexus-surface', className)}>
        <div className="text-text-muted">Loading map...</div>
      </div>
    );
  }

  return (
    <div className={cn('rounded-lg overflow-hidden border border-border-default', className)}>
      <MapContainer
        key={mapId}
        center={center}
        zoom={zoom}
        className="h-full w-full"
        style={{ background: '#0a0a0f', minHeight: '200px' }}
        zoomControl={false}
      >
        {/* Dark theme tile layer - Stadia Maps dark */}
        <TileLayer
          attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
          url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
        />

        <FitBounds devices={devices} />

        {devicesWithLocation.map((device) => {
          const color = device.status === 'online' 
            ? deviceColors[device.type] || '#00ff88'
            : statusColors[device.status];

          return (
            <Marker
              key={device.id}
              position={[device.location!.lat, device.location!.lon]}
              icon={createIcon(color)}
              eventHandlers={{
                click: () => onDeviceClick?.(device),
              }}
            >
              <Popup className="nexus-popup">
                <div className="bg-nexus-surface p-3 rounded-lg min-w-[180px]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono font-semibold text-text-primary">
                      {device.name}
                    </span>
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded-full text-xs',
                        device.status === 'online' && 'bg-neon-green/20 text-neon-green',
                        device.status === 'offline' && 'bg-neon-red/20 text-neon-red',
                        device.status === 'degraded' && 'bg-neon-orange/20 text-neon-orange'
                      )}
                    >
                      {device.status}
                    </span>
                  </div>
                  <div className="space-y-1 text-xs">
                    <p className="text-text-muted">
                      Type: <span className="text-text-secondary capitalize">{device.type}</span>
                    </p>
                    {device.battery !== undefined && (
                      <p className="text-text-muted">
                        Battery: <span className="text-neon-green">{device.battery}%</span>
                      </p>
                    )}
                    <p className="text-text-muted">
                      Captures: <span className="text-neon-cyan">{device.stats.captures}</span>
                    </p>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}


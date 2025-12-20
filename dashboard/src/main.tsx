import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

// Note: StrictMode disabled due to Leaflet compatibility issues
// Leaflet's MapContainer doesn't support React 18's double-mount behavior
// Re-enable StrictMode when react-leaflet supports it
createRoot(document.getElementById('root')!).render(<App />);

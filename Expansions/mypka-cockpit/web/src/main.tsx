import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { AuthGate } from './components/AuthGate';
// INKLINE type (GL-003 §3.1): self-hosted woff2 via @fontsource, bundled by
// Vite. Zero CDN requests: the cockpit runs offline on member machines.
import '@fontsource-variable/bricolage-grotesque'; // Display: headlines
import '@fontsource-variable/instrument-sans'; // Body: the workhorse
import '@fontsource-variable/spline-sans-mono'; // Labels: kickers, timestamps
import '@fontsource-variable/caveat'; // Marginalia - the teacher's hand
import './index.css';
import './cockpit.css';

const el = document.getElementById('root');
if (!el) throw new Error('#root not found');

createRoot(el).render(
  <StrictMode>
    <AuthGate>
      <App />
    </AuthGate>
  </StrictMode>
);

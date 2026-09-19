import { CloudRain, Zap, CloudSnow, Wind } from 'lucide-react';

// ── Geographic Domain Bounding ────────────────────────────────────────────────
export const ASSAM_BOUNDS = [[24.0, 89.8], [28.0, 96.0]];
export const ASSAM_CENTER = [26.2, 92.9];

export const MASK_POSITIONS = [
  [[-90, -360], [90, -360], [90, 360], [-90, 360]],
  [[24.0, 89.8], [28.0, 89.8], [28.0, 96.0], [24.0, 96.0]],
];

// ── WMO Weather Codes & Emojis ────────────────────────────────────────────────
export const WMO = {
  0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
  45: 'Fog', 48: 'Icy fog',
  51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
  61: 'Light rain', 63: 'Rain', 65: 'Heavy rain',
  71: 'Light snow', 73: 'Snow', 75: 'Heavy snow',
  80: 'Showers', 81: 'Heavy showers', 82: 'Violent showers',
  95: 'Thunderstorm', 96: 'Thunderstorm + hail', 99: 'Heavy thunderstorm',
};

export const wmoEmoji = (code) => {
  if (code === 0 || code === 1) return '☀️';
  if (code === 2 || code === 3) return '⛅';
  if (code >= 45 && code <= 48) return '🌫️';
  if (code >= 51 && code <= 67) return '🌧️';
  if (code >= 71 && code <= 77) return '❄️';
  if (code >= 80 && code <= 82) return '🌦️';
  if (code >= 95) return '⛈️';
  return '🌡️';
};

// ── Layers Configuration ──────────────────────────────────────────────────────
export const RAIN_LAYERS = [
  { key: 'current', label: 'Now',   sublabel: 'Observed',   color: '#3b82f6' },
  { key: 'f30',     label: '+30m',  sublabel: 'High skill', color: '#22c55e' },
  { key: 'f60',     label: '+60m',  sublabel: 'High skill', color: '#eab308' },
  { key: 'f90',     label: '+90m',  sublabel: 'Moderate',   color: '#f97316' },
  { key: 'f180',    label: '+3 hr', sublabel: 'Outlook',    color: '#ef4444' },
  { key: 'f360',    label: '+6 hr', sublabel: 'Extended',   color: '#991b1b' },
];

export const HAZARD_LAYERS = [
  { key: 'cloudburst', label: 'Cloudburst', icon: CloudRain, color: '#ea580c' },
  { key: 'hail',       label: 'Hail',       icon: CloudSnow, color: '#2563eb' },
  { key: 'lightning',  label: 'Lightning',  icon: Zap,       color: '#ca8a04' },
  { key: 'downburst',  label: 'Downburst',  icon: Wind,      color: '#7c3aed' },
];

// ── IMD Severity Themes ───────────────────────────────────────────────────────
export const SEVERITY = {
  RED:    { bg: '#450a0a', border: '#dc2626', text: '#f87171', badge: '#dc2626' },
  ORANGE: { bg: '#431407', border: '#ea580c', text: '#fb923c', badge: '#ea580c' },
  YELLOW: { bg: '#422006', border: '#ca8a04', text: '#facc15', badge: '#ca8a04' },
  GREEN:  { bg: '#052e16', border: '#16a34a', text: '#4ade80', badge: '#15803d' },
};

// ── Confidence / Caveat Strings ───────────────────────────────────────────────
export const CONFIDENCE = {
  current: 'Observation frame — no model uncertainty',
  f30:    'PySTEPS + U-Net blend · High skill',
  f60:    'PySTEPS + U-Net blend · High skill',
  f90:    'PySTEPS + U-Net blend · Moderate skill',
  f180:   'Advection outlook · Skill degrades past +2 hr',
  f360:   'Extended outlook · Low confidence beyond +2 hr',
};

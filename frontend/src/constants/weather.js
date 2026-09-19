import { CloudRain, Zap, CloudSnow, Wind } from 'lucide-react';

// ── HUD Palette Tokens ────────────────────────────────────────────────────────
export const HUD_THEME = {
  bgPrimary: '#0B101D',
  bgSurface: '#161F33',
  borderTranslucent: 'rgba(30, 41, 59, 0.6)', // border-slate-800/60
  accentNormal: '#00E676', // Vivid Green
  accentHazard: '#FF1744', // Crimson Red
  accentCyan: '#00B0FF',   // Electric Cyan
};

// ── Geographic Domain Bounding ────────────────────────────────────────────────
export const ASSAM_BOUNDS = [[24.0, 89.8], [28.0, 96.0]];
export const ASSAM_CENTER = [26.2, 92.9];

export const MASK_POSITIONS = [
  [[-90, -360], [90, -360], [90, 360], [-90, 360]],
  [[24.0, 89.8], [28.0, 89.8], [28.0, 96.0], [24.0, 96.0]],
];

// ── IMD Doppler Weather Radar (DWR) & Monitoring City Nodes ──────────────────
export const CITY_NODES = [
  {
    id: 'gau',
    name: 'Guwahati (DWR)',
    code: 'DWR-GAU',
    coords: [26.1445, 91.7362],
    isDwr: true,
    band: 'S-Band 250km',
    rangeMeters: 200000,
    elevation: '55m MSL',
    status: 'ACTIVE',
  },
  {
    id: 'mhb',
    name: 'Mohanbari / Dibrugarh (DWR)',
    code: 'DWR-MHB',
    coords: [27.4728, 94.9120],
    isDwr: true,
    band: 'C-Band 200km',
    rangeMeters: 180000,
    elevation: '108m MSL',
    status: 'ACTIVE',
  },
  {
    id: 'shl',
    name: 'Cherrapunji (DWR)',
    code: 'DWR-SHL',
    coords: [25.2700, 91.7323],
    isDwr: true,
    band: 'S-Band 250km',
    rangeMeters: 200000,
    elevation: '1430m MSL',
    status: 'ACTIVE',
  },
  {
    id: 'agr',
    name: 'Agartala (DWR)',
    code: 'DWR-AGR',
    coords: [23.8315, 91.2868],
    isDwr: true,
    band: 'C-Band 200km',
    rangeMeters: 180000,
    elevation: '15m MSL',
    status: 'STANDBY',
  },
  {
    id: 'tez',
    name: 'Tezpur',
    code: 'AWS-TEZ',
    coords: [26.6528, 92.7926],
    isDwr: false,
    elevation: '48m MSL',
    status: 'OBSERVER',
  },
  {
    id: 'slc',
    name: 'Silchar (Barak Valley)',
    code: 'AWS-SLC',
    coords: [24.8333, 92.7789],
    isDwr: false,
    elevation: '25m MSL',
    status: 'OBSERVER',
  },
  {
    id: 'jrh',
    name: 'Jorhat',
    code: 'AWS-JRH',
    coords: [26.7509, 94.2037],
    isDwr: false,
    elevation: '116m MSL',
    status: 'OBSERVER',
  },
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
export const TIME_OFFSETS = [
  { key: 'current', label: 'Now',   sublabel: 'Observed',   color: '#00B0FF', step: 0 },
  { key: 'f30',     label: '+30m',  sublabel: 'High skill', color: '#00E676', step: 1 },
  { key: 'f60',     label: '+60m',  sublabel: 'High skill', color: '#FFD600', step: 2 },
  { key: 'f90',     label: '+90m',  sublabel: 'Moderate',   color: '#FF9100', step: 3 },
  { key: 'f180',    label: '+3hr',  sublabel: 'Outlook',    color: '#FF3D00', step: 4 },
  { key: 'f360',    label: '+6hr',  sublabel: 'Extended',   color: '#D50000', step: 5 },
];

export const RAIN_LAYERS = TIME_OFFSETS;

export const HAZARD_LAYERS = [
  { key: 'cloudburst', label: 'Cloudburst', icon: CloudRain, color: '#FF1744', desc: 'Rain rate >100mm/hr + OLR index' },
  { key: 'hail',       label: 'Hail',       icon: CloudSnow, color: '#00B0FF', desc: 'Severe updraft + CAPE >1500' },
  { key: 'lightning',  label: 'Lightning',  icon: Zap,       color: '#FFD600', desc: 'Microphysics charge density' },
  { key: 'downburst',  label: 'Downburst',  icon: Wind,      color: '#B388FF', desc: 'Radial velocity shear >15 m/s' },
];

// ── IMD Severity Themes ───────────────────────────────────────────────────────
export const SEVERITY = {
  RED:    { bg: 'rgba(255, 23, 68, 0.15)',  border: '#FF1744', text: '#FF1744', badge: '#FF1744', glow: 'rgba(255, 23, 68, 0.4)' },
  ORANGE: { bg: 'rgba(255, 145, 0, 0.15)', border: '#FF9100', text: '#FF9100', badge: '#FF9100', glow: 'rgba(255, 145, 0, 0.4)' },
  YELLOW: { bg: 'rgba(255, 214, 0, 0.15)', border: '#FFD600', text: '#FFD600', badge: '#FFD600', glow: 'rgba(255, 214, 0, 0.4)' },
  GREEN:  { bg: 'rgba(0, 230, 118, 0.12)',  border: '#00E676', text: '#00E676', badge: '#00E676', glow: 'rgba(0, 230, 118, 0.3)' },
};

// ── Confidence / Caveat Strings ───────────────────────────────────────────────
export const CONFIDENCE = {
  current: 'IMD DWR radar observation sweep · 0 min uncertainty',
  f30:    'PySTEPS Optical Flow + U-Net blend · High CSI (0.68)',
  f60:    'PySTEPS Optical Flow + ConvLSTM blend · High skill',
  f90:    'ConvLSTM temporal state decay · Moderate confidence',
  f180:   'Autoregressive recurrence · Outlook trend',
  f360:   'Extended outlook · Macro-synoptic advection only',
};


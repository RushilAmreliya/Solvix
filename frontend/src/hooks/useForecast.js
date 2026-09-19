import { useState, useEffect, useRef, useCallback } from 'react';

const defaultApiHost =
  typeof window !== 'undefined' && window.location.hostname
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000';
const API_BASE = (import.meta.env.VITE_API_URL || defaultApiHost).replace(/\/$/, '');
const API_URL = `${API_BASE}/api/v1/forecast/latest`;
const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws/forecast';
const RAINVIEWER_API = 'https://api.rainviewer.com/public/weather-maps.json';

export function useForecast() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [connectionMode, setConnectionMode] = useState('connecting');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [rvManifest, setRvManifest] = useState(null);
  const [syncingRadar, setSyncingRadar] = useState(false);

  // Severity debounce — only update badge after 3 consistent readings
  const [displaySeverity, setDisplaySeverity] = useState('GREEN');
  const severityHistory = useRef([]);
  const wsRef = useRef(null);

  // ── Sync Live Radar on-demand ──────────────────────────────────────────────
  const syncLiveRadar = useCallback(async () => {
    setSyncingRadar(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/ingest/sync-live-radar`, { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        if (json.forecast) {
          setData(json.forecast);
          setLastUpdated(new Date().toLocaleTimeString());
        }
      }
    } catch (e) {
      console.error('Failed to sync live radar:', e);
    } finally {
      setSyncingRadar(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadManifest = async () => {
      try {
        const res = await fetch(RAINVIEWER_API);
        if (!res.ok) return;
        const json = await res.json();
        if (mounted) setRvManifest(json);
      } catch {
        /* silent */
      }
    };

    loadManifest();
    const t = setInterval(loadManifest, 5 * 60 * 1000);
    return () => {
      mounted = false;
      clearInterval(t);
    };
  }, []);

  // ── Backend data fetch + WebSocket ─────────────────────────────────────────
  const fetchHttpData = useCallback(async () => {
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
      setLastUpdated(new Date().toLocaleTimeString());
      setConnectionMode((prev) => (prev === 'ws' ? 'ws' : 'http'));
    } catch (err) {
      setError(err.message);
      setConnectionMode('error');
    }
  }, []);

  useEffect(() => {
    let retryCount = 0;
    const MAX_RETRIES = 20;
    let retryTimer = null;

    const connectWS = () => {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;
        ws.onopen = () => {
          setConnectionMode('ws');
          setError(null);
          retryCount = 0;
        };
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'forecast' && msg.data) {
              setData(msg.data);
              setLastUpdated(new Date().toLocaleTimeString());
              setError(null);
              retryCount = 0;
            } else if (msg.type === 'frame_ingested') {
              fetchHttpData();
            }
          } catch {}
        };
        ws.onerror = () => setConnectionMode('http');
        ws.onclose = () => setConnectionMode((p) => (p === 'ws' ? 'http' : p));
      } catch {
        setConnectionMode('http');
      }
    };

    const tryFetch = async () => {
      try {
        const res = await fetch(API_URL, { signal: AbortSignal.timeout(8000) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
        setError(null);
        setLastUpdated(new Date().toLocaleTimeString());
        setConnectionMode((prev) => (prev === 'ws' ? 'ws' : 'http'));
        retryCount = 0;
      } catch (err) {
        const msg = err?.message ?? 'Failed to fetch';
        setError(msg);
        setConnectionMode('error');
        if (retryCount < MAX_RETRIES) {
          retryCount++;
          const delay = Math.min(2000 * retryCount, 10000);
          retryTimer = setTimeout(tryFetch, delay);
        }
      }
    };

    connectWS();
    retryTimer = setTimeout(tryFetch, 500);
    const t1 = setInterval(fetchHttpData, 30000);

    return () => {
      if (retryTimer) clearTimeout(retryTimer);
      clearInterval(t1);
      wsRef.current?.close();
    };
  }, [fetchHttpData]);

  // ── Severity Debounce Filter ───────────────────────────────────────────────
  useEffect(() => {
    if (!data) return;
    const alerts = data.alerts ?? [];
    const current =
      ['RED', 'ORANGE', 'YELLOW', 'GREEN'].find((s) => alerts.some((a) => a.severity === s)) ??
      'GREEN';
    const h = severityHistory.current;
    h.push(current);
    if (h.length > 4) h.shift();
    if (h.length >= 3 && h.slice(-3).every((v) => v === current)) {
      setDisplaySeverity(current);
    }
  }, [data]);

  return {
    data,
    error,
    connectionMode,
    lastUpdated,
    rvManifest,
    syncingRadar,
    displaySeverity,
    fetchHttpData,
    syncLiveRadar,
    apiBase: API_BASE,
  };
}

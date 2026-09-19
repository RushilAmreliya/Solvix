import React, { useState, useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  ImageOverlay,
  Polygon,
  Tooltip,
  CircleMarker,
  Popup,
  Rectangle,
  useMap,
} from 'react-leaflet';
import { Thermometer, Navigation, Droplets, Cpu } from 'lucide-react';
import {
  ASSAM_BOUNDS,
  MASK_POSITIONS,
  RAIN_LAYERS,
  HAZARD_LAYERS,
  CONFIDENCE,
  WMO,
  wmoEmoji,
} from '../constants/weather';
import { LegendRain, LegendHazard } from './Legends';
import LocationWeatherCard from './LocationWeatherCard';
import StatCard from './StatCard';

function FlyTo({ target, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, zoom ?? 10, { duration: 1.2 });
  }, [map, target, zoom]);
  return null;
}

function LockToBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (!map || !bounds) return;
    const applyLock = () => {
      const fitZoom = map.getBoundsZoom(bounds, false, [0, 0]);
      map.setMinZoom(fitZoom);
      map.setMaxBounds(bounds);
      map.fitBounds(bounds, { padding: [0, 0], animate: false });
    };
    applyLock();
    map.on('resize', applyLock);
    return () => map.off('resize', applyLock);
  }, [map, bounds]);
  return null;
}

export default function MapPanel({
  data,
  activeLayer,
  rvTileUrl,
  userLoc,
  localWeather,
  locAddress,
  flyTarget,
  showLocCard,
  setShowLocCard,
}) {
  const [basemapStyle, setBasemapStyle] = useState('satellite');

  const isRainLayer = RAIN_LAYERS.some((l) => l.key === activeLayer);
  const activeRainCfg = RAIN_LAYERS.find((l) => l.key === activeLayer);
  const activeHazCfg = HAZARD_LAYERS.find((l) => l.key === activeLayer);

  const overlayUrl = useMemo(() => data?.images?.[activeLayer], [data, activeLayer]);

  const activePolygons = useMemo(() => {
    if (!data) return [];
    if (activeLayer === 'cloudburst') {
      return (data.cloudburst_polygons ?? []).map((p) => ({ ...p, color: '#ef4444' }));
    }
    if (activeLayer === 'lightning') {
      return (data.lightning_polygons ?? []).map((p) => ({ ...p, color: '#f59e0b' }));
    }
    return [];
  }, [data, activeLayer]);

  const atm = data?.atmospheric_context ?? {};

  return (
    <main className="main-panel">
      {/* Map sub-header */}
      <div className="map-header">
        <div className="map-header-left">
          <span
            className="map-layer-dot"
            style={{ background: isRainLayer ? activeRainCfg?.color : activeHazCfg?.color }}
          />
          <span className="map-title">
            {isRainLayer ? `Precipitation · ${activeRainCfg?.label}` : `${activeHazCfg?.label} Risk`}
          </span>
          {data?.is_live_radar ? (
            <span
              className="live-badge"
              style={{ background: '#064e3b', borderColor: '#059669', color: '#34d399' }}
            >
              <span className="live-dot-anim" style={{ background: '#34d399' }} /> REAL LIVE RADAR
            </span>
          ) : rvTileUrl ? (
            <span className="live-badge">
              <span className="live-dot-anim" /> LIVE Radar
            </span>
          ) : null}
        </div>

        <div className="map-caveat" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              display: 'flex',
              background: '#1e293b',
              borderRadius: 6,
              padding: 2,
              gap: 2,
            }}
          >
            {[
              { id: 'satellite', label: 'Satellite' },
              { id: 'streets', label: 'Streets' },
            ].map((b) => (
              <button
                key={b.id}
                onClick={() => setBasemapStyle(b.id)}
                style={{
                  background: basemapStyle === b.id ? '#3b82f6' : 'transparent',
                  color: basemapStyle === b.id ? '#fff' : '#94a3b8',
                  border: 'none',
                  borderRadius: 4,
                  padding: '2px 8px',
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {b.label}
              </button>
            ))}
          </div>
          <span>{isRainLayer ? CONFIDENCE[activeLayer] : 'IMD threshold verified · +30 min lead'}</span>
        </div>
      </div>

      {/* ── Leaflet Map ── */}
      <div className="map-wrap">
        <MapContainer
          bounds={ASSAM_BOUNDS}
          boundsOptions={{ padding: [0, 0] }}
          maxBounds={ASSAM_BOUNDS}
          maxBoundsViscosity={1.0}
          scrollWheelZoom
          className="map-container"
          style={{ background: '#0f172a' }}
        >
          <LockToBounds bounds={ASSAM_BOUNDS} />
          {flyTarget && <FlyTo target={flyTarget} zoom={10} />}

          {/* Clean High-Resolution Basemaps */}
          {basemapStyle === 'satellite' && (
            <>
              <TileLayer
                key="sat-base"
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution='&copy; <a href="https://www.esri.com/">Esri</a>, Earthstar Geographics'
                bounds={ASSAM_BOUNDS}
                maxZoom={18}
                maxNativeZoom={18}
              />
              <TileLayer
                key="sat-labels"
                url="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                attribution=""
                bounds={ASSAM_BOUNDS}
                maxZoom={18}
                maxNativeZoom={18}
                zIndex={150}
                pane="shadowPane"
              />
            </>
          )}

          {basemapStyle === 'streets' && (
            <TileLayer
              key="streets"
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              bounds={ASSAM_BOUNDS}
              maxZoom={19}
              maxNativeZoom={19}
            />
          )}

          {/* Highlighted box boundary around Assam domain */}
          <Rectangle
            bounds={ASSAM_BOUNDS}
            pathOptions={{ color: '#38bdf8', weight: 3, fill: false, opacity: 1.0 }}
          />

          {/* RainViewer Live Radar */}
          {rvTileUrl && (
            <TileLayer
              key={rvTileUrl}
              url={rvTileUrl}
              attribution='Weather radar &copy; <a href="https://www.rainviewer.com/">RainViewer</a> (free, no API key)'
              bounds={ASSAM_BOUNDS}
              maxNativeZoom={7}
              maxZoom={18}
              opacity={0.65}
              zIndex={200}
            />
          )}

          {/* Mask outside Assam domain */}
          <Polygon
            positions={MASK_POSITIONS}
            pathOptions={{ color: 'none', fillColor: '#0a0f1d', fillOpacity: 1.0 }}
          />

          {/* Nowcast model layer overlay */}
          {overlayUrl && (
            <ImageOverlay url={overlayUrl} bounds={ASSAM_BOUNDS} opacity={0.72} zIndex={300} />
          )}

          {/* Convective hazard polygons */}
          {activePolygons.map((poly, i) => (
            <Polygon
              key={i}
              positions={poly.bounds}
              pathOptions={{ color: poly.color, weight: 2, fillColor: poly.color, fillOpacity: 0.2 }}
            >
              <Tooltip>
                <strong>High Risk Zone</strong>
                <br />
                Risk: {(poly.risk * 100).toFixed(0)}%
              </Tooltip>
            </Polygon>
          ))}

          {/* Geolocation marker */}
          {userLoc && (
            <CircleMarker
              center={[userLoc.lat, userLoc.lng]}
              radius={10}
              pathOptions={{ color: '#60a5fa', fillColor: '#3b82f6', fillOpacity: 0.9, weight: 3 }}
            >
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <strong style={{ color: '#1e293b' }}>{locAddress ?? 'Your Location'}</strong>
                  {localWeather && (
                    <div style={{ marginTop: 6, fontSize: 12, color: '#334155' }}>
                      <div>
                        {wmoEmoji(localWeather.weather_code)} {WMO[localWeather.weather_code] ?? ''}
                      </div>
                      <div>🌡️ {localWeather.temperature_2m?.toFixed(1)}°C</div>
                      <div>💧 Humidity: {localWeather.relative_humidity_2m?.toFixed(0)}%</div>
                      <div>💨 Wind: {localWeather.wind_speed_10m?.toFixed(1)} m/s</div>
                      <div>🌧️ Precip: {localWeather.precipitation?.toFixed(1)} mm</div>
                    </div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          )}
        </MapContainer>

        {/* Legend */}
        <div className="map-legend">
          {isRainLayer ? <LegendRain /> : <LegendHazard type={activeLayer} />}
        </div>

        {/* User location weather card popup */}
        {showLocCard && localWeather && (
          <div className="loc-card-wrap">
            <LocationWeatherCard
              weather={localWeather}
              address={locAddress}
              onClose={() => setShowLocCard(false)}
            />
          </div>
        )}
      </div>

      {/* ── Atmospheric Context Telemetry Row ── */}
      {atm.source && (
        <div className="stats-row">
          <StatCard
            icon={Thermometer}
            label="CAPE"
            value={atm.cape?.toFixed(0) ?? '--'}
            unit=" J/kg"
            sub={
              atm.cape > 2000
                ? '🔴 Extreme instability'
                : atm.cape > 1000
                ? '🟡 Active convection'
                : '🟢 Stable'
            }
            accent="#eab308"
          />
          <StatCard
            icon={Navigation}
            label="Wind"
            value={atm.wind_speed?.toFixed(1) ?? '--'}
            unit=" m/s"
            sub={`${atm.wind_direction?.toFixed(0) ?? '--'}° · 10m AGL`}
            accent="#38bdf8"
          />
          <StatCard
            icon={Droplets}
            label="Humidity"
            value={atm.humidity?.toFixed(0) ?? '--'}
            unit="%"
            sub={atm.humidity >= 85 ? '🔵 High moisture' : '⚪ Normal moisture'}
            accent="#22d3ee"
          />
          <StatCard
            icon={Cpu}
            label="Model"
            value="U-Net + ConvLSTM"
            unit=""
            sub={`PySTEPS · ${atm.source === 'open-meteo' ? '🟢 Live atm.' : '🟡 Cached data'}`}
            accent="#a78bfa"
          />
        </div>
      )}
    </main>
  );
}

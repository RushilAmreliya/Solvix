import React, { useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  ImageOverlay,
  Polygon,
  Tooltip,
  CircleMarker,
  Circle,
  Popup,
  Rectangle,
  useMap,
} from 'react-leaflet';
import { ShieldAlert, MapPin } from 'lucide-react';
import {
  ASSAM_BOUNDS,
  MASK_POSITIONS,
  CITY_NODES,
  WMO,
  wmoEmoji,
} from '../constants/weather';
import LocationWeatherCard from './LocationWeatherCard';

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
  basemapStyle = 'satellite',
  rvTileUrl,
  userLoc,
  localWeather,
  locAddress,
  flyTarget,
  showLocCard,
  setShowLocCard,
}) {
  const overlayUrl = useMemo(() => data?.images?.[activeLayer], [data, activeLayer]);

  const activePolygons = useMemo(() => {
    if (!data) return [];
    if (activeLayer === 'cloudburst') {
      return (data.cloudburst_polygons ?? []).map((p) => ({ ...p, color: '#f43f5e' }));
    }
    if (activeLayer === 'lightning') {
      return (data.lightning_polygons ?? []).map((p) => ({ ...p, color: '#f59e0b' }));
    }
    return [];
  }, [data, activeLayer]);

  return (
    <div className="absolute inset-0 w-full h-full z-0 overflow-hidden bg-[#090D16]">
      {/* ── Seamless Background Map Vignette Overlay ── */}
      <div className="pointer-events-none absolute inset-0 z-[400] shadow-[inset_0_0_120px_50px_#090D16]" />

      <MapContainer
        bounds={ASSAM_BOUNDS}
        boundsOptions={{ padding: [0, 0] }}
        maxBounds={ASSAM_BOUNDS}
        maxBoundsViscosity={1.0}
        scrollWheelZoom
        zoomControl={false}
        className="w-full h-full"
      >
        <LockToBounds bounds={ASSAM_BOUNDS} />
        {flyTarget && <FlyTo target={flyTarget} zoom={10} />}

        {/* ── Clean Basemaps ── */}
        {basemapStyle === 'satellite' ? (
          <>
            <TileLayer
              key="sat-base"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='&copy; Esri, Maxar'
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
              opacity={0.65}
            />
          </>
        ) : (
          <TileLayer
            key="carto-dark"
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; CARTO'
            bounds={ASSAM_BOUNDS}
            maxZoom={19}
            maxNativeZoom={19}
          />
        )}

        {/* ── Subtle Assam Bounding Outline ── */}
        <Rectangle
          bounds={ASSAM_BOUNDS}
          pathOptions={{
            color: '#38bdf8',
            weight: 1.5,
            fill: false,
            opacity: 0.6,
            dashArray: '4, 4',
          }}
        />

        {/* ── Seamless Outer Mask (Deep Slate #090D16) ── */}
        <Polygon
          positions={MASK_POSITIONS}
          pathOptions={{
            color: 'none',
            fillColor: '#090D16',
            fillOpacity: 0.94,
          }}
        />

        {/* ── RainViewer Live Radar Overlay ── */}
        {rvTileUrl && (
          <TileLayer
            key={rvTileUrl}
            url={rvTileUrl}
            bounds={ASSAM_BOUNDS}
            maxNativeZoom={7}
            maxZoom={18}
            opacity={0.65}
            zIndex={200}
          />
        )}

        {/* ── Model Forecast Overlay ── */}
        {overlayUrl && (
          <ImageOverlay
            url={overlayUrl}
            bounds={ASSAM_BOUNDS}
            opacity={0.75}
            zIndex={300}
          />
        )}

        {/* ── Subtle DWR Radar Coverage Circles ── */}
        {CITY_NODES.filter((c) => c.isDwr).map((dwr) => (
          <Circle
            key={`ring-${dwr.id}`}
            center={dwr.coords}
            radius={dwr.rangeMeters ?? 200000}
            pathOptions={{
              color: '#10b981',
              weight: 0.75,
              fill: true,
              fillColor: '#10b981',
              fillOpacity: 0.02,
              dashArray: '3, 6',
              opacity: 0.35,
            }}
          />
        ))}

        {/* ── Minimalist City & Station Markers ── */}
        {CITY_NODES.map((city) => (
          <CircleMarker
            key={`node-${city.id}`}
            center={city.coords}
            radius={city.isDwr ? 5 : 3.5}
            pathOptions={{
              color: city.isDwr ? '#10b981' : '#38bdf8',
              fillColor: city.isDwr ? '#10b981' : '#0f172a',
              fillOpacity: 0.9,
              weight: 1.5,
            }}
          >
            <Tooltip direction="top" offset={[0, -6]} opacity={0.95}>
              <div className="text-[11px] font-mono-num font-medium text-slate-200 bg-slate-900/90 px-2 py-0.5 rounded border border-white/10 shadow-lg">
                <span className={city.isDwr ? 'text-emerald-400 font-bold' : 'text-sky-400'}>
                  {city.code}
                </span>{' '}
                {city.name}
              </div>
            </Tooltip>
            <Popup>
              <div className="p-1 min-w-[170px] text-slate-900 font-sans">
                <div className="flex items-center justify-between border-b pb-1 mb-1.5">
                  <strong className="text-xs font-semibold text-slate-900">{city.name}</strong>
                  <span className={`text-[9px] px-1 py-0.2 rounded font-semibold ${
                    city.isDwr ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {city.status}
                  </span>
                </div>
                <div className="text-xs text-slate-600 space-y-0.5 font-mono-num">
                  <div>Station: {city.code}</div>
                  <div>Elev: {city.elevation}</div>
                  {city.isDwr && <div className="text-emerald-700 font-medium font-sans mt-1">IMD Doppler Radar</div>}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* ── Convective Hazard Risk Polygons ── */}
        {activePolygons.map((poly, i) => (
          <Polygon
            key={`poly-${i}`}
            positions={poly.bounds}
            pathOptions={{
              color: poly.color,
              weight: 1.5,
              fillColor: poly.color,
              fillOpacity: 0.22,
            }}
          >
            <Tooltip opacity={0.95}>
              <div className="text-xs font-mono-num bg-slate-950 p-2 rounded border border-rose-500/30 text-white">
                <div className="text-rose-400 font-semibold flex items-center gap-1">
                  <ShieldAlert size={12} /> Severe Risk Area
                </div>
                <div className="text-[11px] text-slate-300 mt-0.5">
                  Intensity: {(poly.risk * 100).toFixed(0)}%
                </div>
              </div>
            </Tooltip>
          </Polygon>
        ))}

        {/* ── User Geolocation Marker ── */}
        {userLoc && (
          <CircleMarker
            center={[userLoc.lat, userLoc.lng]}
            radius={7}
            pathOptions={{
              color: '#38bdf8',
              fillColor: '#0ea5e9',
              fillOpacity: 0.95,
              weight: 2,
            }}
          >
            <Popup>
              <div className="p-1 min-w-[190px] text-slate-900">
                <strong className="text-xs flex items-center gap-1 text-slate-900 font-semibold">
                  <MapPin size={13} className="text-sky-600" />
                  {locAddress ?? 'Your Location'}
                </strong>
                {localWeather && (
                  <div className="mt-1.5 text-xs text-slate-700 space-y-0.5">
                    <div>{wmoEmoji(localWeather.weather_code)} {WMO[localWeather.weather_code] ?? ''}</div>
                    <div>Temp: <strong>{localWeather.temperature_2m?.toFixed(1)}°C</strong></div>
                    <div>Humidity: <strong>{localWeather.relative_humidity_2m?.toFixed(0)}%</strong></div>
                    <div>Wind: <strong>{localWeather.wind_speed_10m?.toFixed(1)} m/s</strong></div>
                  </div>
                )}
              </div>
            </Popup>
          </CircleMarker>
        )}
      </MapContainer>

      {/* Floating Location Weather Popup Card */}
      {showLocCard && localWeather && (
        <div className="absolute top-20 right-6 z-[1001]">
          <LocationWeatherCard
            weather={localWeather}
            address={locAddress}
            onClose={() => setShowLocCard(false)}
          />
        </div>
      )}
    </div>
  );
}

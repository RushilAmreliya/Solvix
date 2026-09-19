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
      return (data.cloudburst_polygons ?? []).map((p) => ({ ...p, color: '#FF1744' }));
    }
    if (activeLayer === 'lightning') {
      return (data.lightning_polygons ?? []).map((p) => ({ ...p, color: '#FFD600' }));
    }
    return [];
  }, [data, activeLayer]);

  return (
    <div className="absolute inset-0 w-full h-full z-0 overflow-hidden bg-[#070b14]">
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

        {/* ── High-Resolution Basemaps ── */}
        {basemapStyle === 'satellite' ? (
          <>
            {/* Esri World Imagery */}
            <TileLayer
              key="sat-base"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution='&copy; Esri, Maxar, Earthstar Geographics'
              bounds={ASSAM_BOUNDS}
              maxZoom={18}
              maxNativeZoom={18}
            />
            {/* High contrast administrative boundaries & place labels */}
            <TileLayer
              key="sat-labels"
              url="https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
              attribution=""
              bounds={ASSAM_BOUNDS}
              maxZoom={18}
              maxNativeZoom={18}
              zIndex={150}
              pane="shadowPane"
              opacity={0.8}
            />
          </>
        ) : (
          /* Dark CartoDB Matter / Street Map */
          <TileLayer
            key="carto-dark"
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            bounds={ASSAM_BOUNDS}
            maxZoom={19}
            maxNativeZoom={19}
          />
        )}

        {/* ── High-Contrast Convective Monitoring Domain Bounding Box (Assam) ── */}
        <Rectangle
          bounds={ASSAM_BOUNDS}
          pathOptions={{
            color: '#00B0FF',
            weight: 2.5,
            fill: false,
            opacity: 0.9,
            dashArray: '6, 6',
          }}
        />

        {/* ── Outer Domain Mask ── */}
        <Polygon
          positions={MASK_POSITIONS}
          pathOptions={{
            color: 'none',
            fillColor: '#070b14',
            fillOpacity: 0.92,
          }}
        />

        {/* ── RainViewer Live Doppler Radar Sweep Overlay ── */}
        {rvTileUrl && (
          <TileLayer
            key={rvTileUrl}
            url={rvTileUrl}
            attribution='Weather radar &copy; RainViewer'
            bounds={ASSAM_BOUNDS}
            maxNativeZoom={7}
            maxZoom={18}
            opacity={0.65}
            zIndex={200}
          />
        )}

        {/* ── NowCast Fusion Model Output (U-Net + ConvLSTM + PySTEPS) ── */}
        {overlayUrl && (
          <ImageOverlay
            url={overlayUrl}
            bounds={ASSAM_BOUNDS}
            opacity={0.76}
            zIndex={300}
          />
        )}

        {/* ── IMD Doppler Weather Radar (DWR) Range Rings ── */}
        {CITY_NODES.filter((c) => c.isDwr).map((dwr) => (
          <React.Fragment key={`ring-${dwr.id}`}>
            <Circle
              center={dwr.coords}
              radius={dwr.rangeMeters ?? 200000}
              pathOptions={{
                color: '#00E676',
                weight: 1,
                fill: true,
                fillColor: '#00E676',
                fillOpacity: 0.03,
                dashArray: '4, 8',
              }}
            />
            <Circle
              center={dwr.coords}
              radius={(dwr.rangeMeters ?? 200000) / 2}
              pathOptions={{
                color: '#00B0FF',
                weight: 0.75,
                fill: false,
                dashArray: '2, 6',
                opacity: 0.4,
              }}
            />
          </React.Fragment>
        ))}

        {/* ── City & Radar Station Node Markers ── */}
        {CITY_NODES.map((city) => (
          <CircleMarker
            key={`node-${city.id}`}
            center={city.coords}
            radius={city.isDwr ? 7 : 4.5}
            pathOptions={{
              color: city.isDwr ? '#00E676' : '#00B0FF',
              fillColor: city.isDwr ? '#00E676' : '#161F33',
              fillOpacity: 0.9,
              weight: 2,
            }}
          >
            <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
              <div className="text-[11px] font-mono-num font-bold text-slate-100 bg-slate-950/90 px-2 py-1 rounded border border-slate-700">
                <span className={city.isDwr ? 'text-emerald-400' : 'text-cyan-400'}>
                  [{city.code}]
                </span>{' '}
                {city.name}
                {city.isDwr && <span className="block text-[9px] text-slate-400 font-normal">{city.band}</span>}
              </div>
            </Tooltip>
            <Popup>
              <div className="p-1 min-w-[190px] font-mono-num text-slate-900">
                <div className="flex items-center justify-between border-b pb-1 mb-1.5">
                  <strong className="text-xs font-bold text-slate-900">{city.name}</strong>
                  <span className={`text-[10px] px-1 py-0.5 rounded font-bold ${
                    city.isDwr ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'
                  }`}>
                    {city.status}
                  </span>
                </div>
                <div className="text-[11px] text-slate-600 space-y-1">
                  <div>Station Code: <strong>{city.code}</strong></div>
                  <div>Coords: {city.coords[0].toFixed(2)}°N, {city.coords[1].toFixed(2)}°E</div>
                  <div>Elevation: {city.elevation}</div>
                  {city.isDwr && (
                    <div className="text-emerald-700 font-semibold pt-0.5">
                      Operational Doppler Radar (IMD)
                    </div>
                  )}
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
              weight: 2,
              fillColor: poly.color,
              fillOpacity: 0.25,
            }}
          >
            <Tooltip opacity={0.95}>
              <div className="text-xs font-mono-num bg-slate-950 p-2 rounded border border-red-500/50 text-white">
                <strong className="text-red-400 flex items-center gap-1">
                  <ShieldAlert size={13} /> Severe Hazard Zone
                </strong>
                <div className="mt-1">
                  Calculated Risk: <span className="font-bold">{(poly.risk * 100).toFixed(0)}%</span>
                </div>
              </div>
            </Tooltip>
          </Polygon>
        ))}

        {/* ── User Geolocation Marker ── */}
        {userLoc && (
          <CircleMarker
            center={[userLoc.lat, userLoc.lng]}
            radius={9}
            pathOptions={{
              color: '#00E676',
              fillColor: '#00B0FF',
              fillOpacity: 0.95,
              weight: 2.5,
            }}
          >
            <Popup>
              <div className="p-1 min-w-[200px] text-slate-900">
                <strong className="text-xs text-slate-900 flex items-center gap-1">
                  <MapPin size={13} className="text-blue-600" />
                  {locAddress ?? 'Your Location'}
                </strong>
                {localWeather && (
                  <div className="mt-2 text-xs text-slate-700 space-y-0.5">
                    <div>
                      {wmoEmoji(localWeather.weather_code)} {WMO[localWeather.weather_code] ?? ''}
                    </div>
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
        <div className="absolute top-20 right-4 z-[1001]">
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

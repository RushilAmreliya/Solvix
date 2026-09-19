import { useState, useCallback } from 'react';

export function useUserLocation() {
  const [userLoc, setUserLoc] = useState(null);
  const [localWeather, setLocalWeather] = useState(null);
  const [locAddress, setLocAddress] = useState(null);
  const [locating, setLocating] = useState(false);
  const [flyTarget, setFlyTarget] = useState(null);
  const [showLocCard, setShowLocCard] = useState(false);

  const locateUser = useCallback(() => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setUserLoc({ lat, lng });
        setFlyTarget([lat, lng]);
        setShowLocCard(true);
        setLocating(false);

        // Reverse-geocode via OSM Nominatim (free, no key)
        try {
          const gr = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
            { headers: { 'Accept-Language': 'en' } }
          );
          const gj = await gr.json();
          const addr = gj.address;
          setLocAddress(
            addr?.city ?? addr?.town ?? addr?.village ?? addr?.county ?? 'Your Location'
          );
        } catch {
          setLocAddress('Your Location');
        }

        // Fetch local weather from Open-Meteo
        try {
          const wr = await fetch(
            `https://api.open-meteo.com/v1/forecast` +
              `?latitude=${lat}&longitude=${lng}` +
              `&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,weather_code` +
              `&wind_speed_unit=ms&timezone=auto`
          );
          const wj = await wr.json();
          setLocalWeather(wj.current ?? null);
        } catch {
          setLocalWeather(null);
        }
      },
      (err) => {
        setLocating(false);
        if (err.code === 1) {
          alert('Location permission denied. Please allow location access and try again.');
        } else {
          alert('Could not get your location. Try again.');
        }
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  }, []);

  return {
    userLoc,
    localWeather,
    locAddress,
    locating,
    flyTarget,
    showLocCard,
    setShowLocCard,
    locateUser,
  };
}

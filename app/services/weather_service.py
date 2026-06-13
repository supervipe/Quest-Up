import httpx


class WeatherService:
    async def get_current_weather(self, lat: float | None, lng: float | None) -> dict:
        latitude = lat or 49.2827
        longitude = lng or -123.1207
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
                response.raise_for_status()
        except httpx.HTTPError:
            return self._fallback(latitude, longitude)

        current = response.json().get("current", {})
        return {
            "provider": "open-meteo",
            "condition": self._weather_code_to_condition(current.get("weather_code")),
            "temperature_c": current.get("temperature_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_10m_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "observed_at": current.get("time"),
            "lat": latitude,
            "lng": longitude,
        }

    def _fallback(self, lat: float, lng: float) -> dict:
        return {
            "provider": "mock-fallback",
            "condition": "clear",
            "temperature_c": 18,
            "lat": lat,
            "lng": lng,
        }

    def _weather_code_to_condition(self, code: int | None) -> str:
        if code is None:
            return "unknown"
        if code == 0:
            return "clear"
        if code in {1, 2, 3}:
            return "cloudy"
        if code in {45, 48}:
            return "fog"
        if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
            return "rain"
        if code in {71, 73, 75, 77, 85, 86}:
            return "snow"
        if code in {95, 96, 99}:
            return "thunderstorm"
        return "other"

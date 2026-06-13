import httpx

from app.core.config import get_settings


class LocationService:
    async def find_nearby_places(self, lat: float | None, lng: float | None, radius_km: float = 5) -> list[dict]:
        settings = get_settings()
        if settings.google_places_api_key and lat is not None and lng is not None:
            places = await self._google_places(lat, lng, radius_km, settings.google_places_api_key)
            if places:
                return places
        return self._mock_places(lat, lng)

    async def _google_places(self, lat: float, lng: float, radius_km: float, api_key: str) -> list[dict]:
        payload = {
            "includedTypes": ["park", "cafe", "library", "restaurant", "tourist_attraction", "gym"],
            "maxResultCount": 10,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": min(radius_km * 1000, 50000),
                }
            },
        }
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.location,places.types",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post("https://places.googleapis.com/v1/places:searchNearby", json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError:
            return []
        return [self._normalize_google_place(place, lat, lng) for place in response.json().get("places", [])]

    def _normalize_google_place(self, place: dict, lat: float, lng: float) -> dict:
        location = place.get("location", {})
        place_lat = location.get("latitude", lat)
        place_lng = location.get("longitude", lng)
        types = place.get("types", [])
        return {
            "name": place.get("displayName", {}).get("text", "Nearby place"),
            "place_type": self._place_type(types),
            "lat": place_lat,
            "lng": place_lng,
            "distance_m": round(((place_lat - lat) ** 2 + (place_lng - lng) ** 2) ** 0.5 * 111_000, 1),
        }

    def _place_type(self, types: list[str]) -> str:
        for candidate in ["park", "cafe", "library", "restaurant", "gym"]:
            if candidate in types:
                return candidate
        if "tourist_attraction" in types:
            return "mural"
        return types[0] if types else "place"

    def _mock_places(self, lat: float | None, lng: float | None) -> list[dict]:
        base_lat = lat or 49.2827
        base_lng = lng or -123.1207
        return [
            {"name": "Harbor Green Park", "place_type": "park", "lat": base_lat + 0.003, "lng": base_lng, "distance_m": 420},
            {"name": "Side Quest Cafe", "place_type": "cafe", "lat": base_lat, "lng": base_lng + 0.004, "distance_m": 610},
            {"name": "Community Library", "place_type": "library", "lat": base_lat - 0.002, "lng": base_lng, "distance_m": 530},
            {"name": "Hidden Mural Alley", "place_type": "mural", "lat": base_lat, "lng": base_lng - 0.003, "distance_m": 350},
        ]

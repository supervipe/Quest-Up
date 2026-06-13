from fastapi import APIRouter, Query

from app.services.location_service import LocationService
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/external", tags=["external-api-smoke"])


@router.get("/weather")
async def weather(lat: float = Query(49.2827), lng: float = Query(-123.1207)):
    return await WeatherService().get_current_weather(lat, lng)


@router.get("/places")
async def places(lat: float = Query(49.2827), lng: float = Query(-123.1207), radius_km: float = Query(5)):
    return await LocationService().find_nearby_places(lat, lng, radius_km)

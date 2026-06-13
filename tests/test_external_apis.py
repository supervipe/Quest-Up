import os

import pytest

from app.services.location_service import LocationService
from app.services.weather_service import WeatherService

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(os.getenv("RUN_EXTERNAL_API_TESTS") != "1", reason="Set RUN_EXTERNAL_API_TESTS=1 to run external API smoke checks")
async def test_external_api_service_smoke():
    weather = await WeatherService().get_current_weather(49.2827, -123.1207)
    places = await LocationService().find_nearby_places(49.2827, -123.1207, 5)
    assert "condition" in weather
    assert isinstance(places, list)

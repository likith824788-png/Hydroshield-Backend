"""
OpenWeather API Weather Service
Fetches live weather data for a given latitude/longitude.
Requires: OPENWEATHER_API_KEY in .env
"""
import httpx
from ..config import settings


async def fetch_weather(latitude: float, longitude: float) -> dict:
    """
    Fetch real-time weather from OpenWeather API.
    Returns a normalized weather data dict for use in flood prediction.

    Raises:
        ValueError: If the API key is not configured.
        httpx.HTTPStatusError: On non-2xx API responses.
    """
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key or api_key in ("", "your_openweather_api_key_here"):
        raise ValueError(
            "OpenWeather API key is not configured. "
            "Set OPENWEATHER_API_KEY in your .env file."
        )

    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": api_key,
        "units": "metric",
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(settings.OPENWEATHER_URL, params=params)
        response.raise_for_status()
        data = response.json()

    # Parse OpenWeather response fields
    main = data.get("main", {})
    wind = data.get("wind", {})
    rain = data.get("rain", {})
    weather_list = data.get("weather", [{}])
    weather_desc = weather_list[0] if weather_list else {}

    temperature = round(main.get("temp", 0), 1)
    feels_like = round(main.get("feels_like", 0), 1)
    humidity = round(main.get("humidity", 0), 1)

    # Convert wind m/s → km/h
    wind_speed_ms = wind.get("speed", 0)
    wind_speed_kmh = round(wind_speed_ms * 3.6, 1)
    wind_direction = wind.get("deg", 0)

    # Rain in last 1 hour (mm); OpenWeather free tier only provides 1h
    precipitation = round(rain.get("1h", 0.0), 2)

    condition = weather_desc.get("description", "").title() or "Clear"
    weather_code = weather_desc.get("id", 800)

    return {
        "temperature": temperature,
        "apparent_temperature": feels_like,
        "humidity": humidity,
        "wind_speed": wind_speed_kmh,
        "wind_direction": wind_direction,
        "precipitation": precipitation,
        "recent_rainfall_6h": precipitation,   # Proxy; free tier gives 1h only
        "weather_code": weather_code,
        "condition": condition,
        "latitude": latitude,
        "longitude": longitude,
    }

from fastapi import APIRouter, HTTPException
from ..services.weather_service import fetch_weather
from ..services.flood_prediction import calculate_flood_prediction
from ..database import get_database
from ..config import settings

router = APIRouter(prefix="/flood", tags=["Flood Prediction"])


@router.get("/prediction")
async def get_flood_prediction(
    latitude: float = None,
    longitude: float = None,
):
    db = await get_database()
    if latitude is None or longitude is None:
        try:
            saved = await db["settings"].find_one({})
            if saved:
                latitude = saved.get("latitude", settings.DEFAULT_LATITUDE)
                longitude = saved.get("longitude", settings.DEFAULT_LONGITUDE)
            else:
                latitude = settings.DEFAULT_LATITUDE
                longitude = settings.DEFAULT_LONGITUDE
        except Exception:
            latitude = settings.DEFAULT_LATITUDE
            longitude = settings.DEFAULT_LONGITUDE

    try:
        weather = await fetch_weather(latitude, longitude)
        prediction = calculate_flood_prediction(
            rainfall=weather["precipitation"],
            humidity=weather["humidity"],
            wind_speed=weather["wind_speed"],
            temperature=weather["temperature"],
            recent_rainfall_6h=weather["recent_rainfall_6h"],
        )
        return {
            "success": True,
            "data": {
                **prediction,
                "weather_snapshot": weather,
                "location": {"latitude": latitude, "longitude": longitude},
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Prediction error: {str(e)}")

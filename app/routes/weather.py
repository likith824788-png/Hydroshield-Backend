from fastapi import APIRouter, HTTPException
from ..services.weather_service import fetch_weather
from ..database import get_database
from ..config import settings

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("")
async def get_weather(
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
        return {"success": True, "data": weather}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Weather service error: {str(e)}")

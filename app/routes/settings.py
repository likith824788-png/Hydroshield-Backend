"""
Settings Route
GET /api/settings  — Retrieve current location/system settings
PUT /api/settings  — Update location settings (updates memory cache & MongoDB)
"""
from fastapi import APIRouter
from ..database import get_database
from ..models.settings_model import AppSettings
from ..config import settings as env_settings

router = APIRouter(prefix="/settings", tags=["Settings"])

# ── In-memory fallback (initialised from .env defaults) ───────────────────────
_SETTINGS_CACHE: dict = {
    "latitude":                 env_settings.DEFAULT_LATITUDE,
    "longitude":                env_settings.DEFAULT_LONGITUDE,
    "location_name":            env_settings.DEFAULT_LOCATION_NAME,
    "refresh_interval_seconds": 30,
    "api_base_url":             "http://localhost:8000/api",
    "openweather_api_key":      "",
    "resend_api_key":           "",
    "resend_from_email":        "",
    "enable_email_notifications": False,
    "enable_citizen_alerts":    False,
    "alert_recipient_email":    "",
}


@router.get("")
async def get_settings():
    """Return current application settings."""
    try:
        db    = await get_database()
        saved = await db["settings"].find_one({}, {"_id": 0})
        if saved:
            return {"success": True, "data": {**_SETTINGS_CACHE, **saved}}
    except Exception as e:
        print(f"[Settings] MongoDB read error: {e}")
    return {"success": True, "data": _SETTINGS_CACHE}


@router.put("")
async def update_settings(new_settings: AppSettings):
    """
    Save updated location settings.
    Updates memory cache instantly, then persists to MongoDB.
    """
    global _SETTINGS_CACHE
    data = new_settings.model_dump()
    _SETTINGS_CACHE = {**_SETTINGS_CACHE, **data}

    # Attempt MongoDB update in background without blocking response
    try:
        db = await get_database()
        await db["settings"].replace_one({}, data, upsert=True)
        print(f"[Settings] Updated: {data.get('location_name')} ({data.get('latitude')}, {data.get('longitude')})")
    except Exception as e:
        print(f"[Settings] MongoDB write skipped: {e}")

    return {
        "success": True,
        "data":    _SETTINGS_CACHE,
        "message": f"Settings saved for {data.get('location_name', 'Location')}",
    }

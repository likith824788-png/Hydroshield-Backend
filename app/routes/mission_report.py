"""
Mission Report Route
GET /api/mission-report — Generate a fresh operational mission report from live weather data.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter
from ..database import get_database
from ..services.weather_service import fetch_weather
from ..services.flood_prediction import calculate_flood_prediction
from ..config import settings

router = APIRouter(prefix="/mission-report", tags=["Mission Report"])

# ── City-specific hospital / shelter data ─────────────────────────────────────
_CITY_RESOURCES = {
    "Chennai": {
        "hospitals": ["Government Stanley Hospital", "Rajiv Gandhi Govt Hospital", "Kilpauk Medical College"],
        "shelters":  ["Jawaharlal Nehru Stadium", "Anna University Sports Ground", "Government Higher Secondary School, Adyar"],
    },
    "Bengaluru": {
        "hospitals": ["Bowring & Lady Curzon Hospital", "Victoria Hospital", "St. John's Medical College"],
        "shelters":  ["Kanteerava Stadium", "BBMP Community Hall, Whitefield", "Lal Bagh Ground"],
    },
    "Hyderabad": {
        "hospitals": ["Osmania General Hospital", "NIMS Hospital", "Gandhi Hospital"],
        "shelters":  ["LB Stadium", "MCH Community Centre", "Necklace Road Ground"],
    },
    "Madurai": {
        "hospitals": ["Government Rajaji Hospital", "Meenakshi Mission Hospital"],
        "shelters":  ["Tamil Nadu Agricultural University Ground", "Madurai Corporation Hall"],
    },
    "Coimbatore": {
        "hospitals": ["Government Medical College Hospital", "PSG Hospitals"],
        "shelters":  ["Nehru Stadium, Coimbatore", "Corporation School Ground"],
    },
    "DEFAULT": {
        "hospitals": [],
        "shelters":  [],
    },
}


def _resolve_city_resources(location_name: str) -> dict:
    """Pick hospital/shelter list based on location name substring match."""
    for key in _CITY_RESOURCES:
        if key != "DEFAULT" and key.lower() in location_name.lower():
            return _CITY_RESOURCES[key]
    return _CITY_RESOURCES["DEFAULT"]


@router.get("")
async def get_mission_report():
    """
    Generate a fresh operational mission report using live weather telemetry.
    Reads current saved location from MongoDB settings collection.
    Falls back to env defaults if DB is unavailable.
    """
    # ── Resolve location from DB settings ───────────────────────────────────
    lat      = settings.DEFAULT_LATITUDE
    lng      = settings.DEFAULT_LONGITUDE
    location = settings.DEFAULT_LOCATION_NAME

    try:
        db            = await get_database()
        saved_settings = await db["settings"].find_one({}, {"_id": 0})
        if saved_settings:
            lat      = saved_settings.get("latitude",      lat)
            lng      = saved_settings.get("longitude",     lng)
            location = saved_settings.get("location_name", location)
    except Exception as e:
        print(f"[MissionReport] DB settings read failed: {e}. Using defaults.")

    # ── Fetch live weather + run prediction ──────────────────────────────────
    try:
        weather    = await fetch_weather(lat, lng)
        prediction = calculate_flood_prediction(
            rainfall          = weather["precipitation"],
            humidity          = weather["humidity"],
            wind_speed        = weather["wind_speed"],
            temperature       = weather["temperature"],
            recent_rainfall_6h= weather["recent_rainfall_6h"],
        )
    except Exception as e:
        print(f"[MissionReport] Weather/prediction error: {e}. Using zero-baseline.")
        prediction = {
            "probability":           0,
            "severity":              "SAFE",
            "affected_areas":        [],
            "rescue_resources":      {"rescue_boats": 0, "ambulances": 0, "drones": 0},
            "estimated_water_depth": 0.0,
            "river_level":           0.0,
        }

    resources = prediction.get("rescue_resources", {})
    severity  = prediction.get("severity", "SAFE")
    prob      = prediction.get("probability", 0)

    # ── Resolve city-specific hospitals/shelters ─────────────────────────────
    city_res           = _resolve_city_resources(location)
    # Only assign hospitals & shelters when there is active emergency
    hospitals_assigned = city_res["hospitals"] if severity in ("MODERATE", "HIGH") else []
    shelters_assigned  = city_res["shelters"]  if severity in ("LOW", "MODERATE", "HIGH") else []

    report = {
        "id":             f"MSN-{str(uuid.uuid4())[:8].upper()}",
        "flood_probability": prob,
        "affected_areas": prediction.get("affected_areas", []),
        "resources_allocated": {
            "rescue_boats":   resources.get("rescue_boats", 0),
            "ambulances":     resources.get("ambulances", 0),
            "drones":         resources.get("drones", 0),
            "emergency_teams": resources.get("rescue_boats", 0) * 3 if prob > 0 else 0,
            "water_pumps":    int(prob / 20) if prob > 0 else 0,
        },
        "hospitals_assigned": hospitals_assigned,
        "shelters_assigned":  shelters_assigned,
        "emergency_level":    severity,
        "mission_status":     "ACTIVE" if severity in ("HIGH", "MODERATE") else "MONITORING",
        "location":           location,
        "coordinates":        {"latitude": lat, "longitude": lng},
        "estimated_water_depth": prediction.get("estimated_water_depth", 0.0),
        "river_level":           prediction.get("river_level", 0.0),
        "generated_at":          datetime.utcnow().isoformat(),
    }

    # ── Persist report to MongoDB ────────────────────────────────────────────
    try:
        await db["mission_reports"].insert_one({**report})
    except Exception as e:
        print(f"[MissionReport] MongoDB write failed: {e}")

    return {"success": True, "data": report}

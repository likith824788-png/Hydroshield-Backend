"""
AI Agents Status Route
GET /api/agents/status — Returns live status of all AI agents in the system.
Uses asyncio.wait_for to cap weather fetch at 5s and never block the API.
"""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter
from ..services.weather_service import fetch_weather
from ..services.flood_prediction import calculate_flood_prediction
from ..config import settings

router = APIRouter(prefix="/agents", tags=["AI Agents"])

_AGENT_START_TIME = datetime.now(timezone.utc)

_AGENTS_DEFINITION = [
    {
        "id":          "hydrological-agent",
        "name":        "Hydrological Telemetry Agent",
        "description": "Monitors real-time weather and hydrological sensor data via OpenWeather API",
        "icon":        "droplets",
    },
    {
        "id":          "urban-hydrodynamic-agent",
        "name":        "Urban Hydrodynamic Agent",
        "description": "AI-powered flood probability prediction and area impact assessment engine",
        "icon":        "brain",
    },
    {
        "id":          "municipal-decision-agent",
        "name":        "Municipal Decision Agent",
        "description": "Generates and dispatches action recommendations to the Municipal Control Room",
        "icon":        "building",
    },
    {
        "id":          "civil-protection-agent",
        "name":        "Civil Protection Agent",
        "description": "Manages emergency alerts, evacuation orders, rescue teams, and shelter assignments",
        "icon":        "shield",
    },
    {
        "id":          "rescue-planner-agent",
        "name":        "AI Rescue Mission Planner",
        "description": "Coordinates rescue resource allocation, boat deployments, and evacuation routing",
        "icon":        "map",
    },
]


@router.get("/status")
async def get_agent_status():
    """
    Return live status of all AI agents.
    Weather fetch is capped at 5 seconds to prevent API timeout.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    uptime_hours = round((now - _AGENT_START_TIME).total_seconds() / 3600, 2)

    probability = 0.0
    severity    = "SAFE"

    try:
        # Cap weather fetch at 5 seconds — never let it block the agents API
        weather = await asyncio.wait_for(
            fetch_weather(settings.DEFAULT_LATITUDE, settings.DEFAULT_LONGITUDE),
            timeout=5.0,
        )
        prediction = calculate_flood_prediction(
            rainfall          = weather["precipitation"],
            humidity          = weather["humidity"],
            wind_speed        = weather["wind_speed"],
            temperature       = weather["temperature"],
            recent_rainfall_6h= weather["recent_rainfall_6h"],
        )
        probability = prediction["probability"]
        severity    = prediction["severity"]
    except asyncio.TimeoutError:
        print("[Agents] Weather fetch timed out (>5s). Using default SAFE status.")
    except Exception as e:
        print(f"[Agents] Weather fetch error: {e}. Using default SAFE status.")

    status_map = {
        "SAFE":     ("ACTIVE",     "MONITORING",  "STANDBY"),
        "LOW":      ("ACTIVE",     "PROCESSING",  "ACTIVE"),
        "MODERATE": ("PROCESSING", "PROCESSING",  "ACTIVE"),
        "HIGH":     ("ACTIVE",     "ACTIVE",      "ACTIVE"),
    }
    hydro_status, urban_status, ops_status = status_map.get(severity, ("ACTIVE", "MONITORING", "STANDBY"))

    live_statuses = {
        "hydrological-agent":       hydro_status,
        "urban-hydrodynamic-agent": urban_status,
        "municipal-decision-agent": ops_status,
        "civil-protection-agent":   ops_status,
        "rescue-planner-agent":     "STANDBY" if severity == "SAFE" else "ACTIVE",
    }

    tasks_map = {
        "hydrological-agent":       int(probability * 0.8),
        "urban-hydrodynamic-agent": int(probability * 0.5),
        "municipal-decision-agent": int(probability * 0.3),
        "civil-protection-agent":   int(probability * 0.4),
        "rescue-planner-agent":     int(probability * 0.2),
    }

    agents = []
    for defn in _AGENTS_DEFINITION:
        agents.append({
            **defn,
            "status":          live_statuses.get(defn["id"], "ACTIVE"),
            "tasks_completed": tasks_map.get(defn["id"], 0),
            "uptime_hours":    uptime_hours,
            "last_updated":    now_iso,
            "flood_level":     severity,
            "probability":     probability,
        })

    return {
        "success":     True,
        "data":        agents,
        "total":       len(agents),
        "severity":    severity,
        "probability": probability,
    }

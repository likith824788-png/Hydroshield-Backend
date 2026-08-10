"""
AI Flood Prediction Engine
Hydrodynamic calculation model using real-time weather telemetry.
All values baseline at 0 when conditions are safe.
"""
from typing import Dict, List

# ── Flood-prone area labels per severity ──────────────────────────────────────
FLOOD_PRONE_AREAS: Dict[str, List[str]] = {
    "HIGH": [
        "Downtown Riverside District",
        "Lower Market Area",
        "Coastal Zone Alpha",
        "Bridge Street Corridor",
        "Flood Plain Zone B",
        "Industrial Canal Belt",
    ],
    "MODERATE": [
        "Northern Industrial Park",
        "Residential Block 7",
        "Shopping District East",
        "Southern Bypass Road",
    ],
    "LOW": [
        "Uptown Heights",
        "University Campus Area",
        "Technology Park Zone",
    ],
    "SAFE": [],
}

# ── AI-generated recommended actions per severity ─────────────────────────────
RECOMMENDED_ACTIONS: Dict[str, List[str]] = {
    "HIGH": [
        "Activate all pump stations immediately",
        "Open flood gates (Gate A, B, C)",
        "Close all low-lying road access",
        "Deploy temporary flood barriers",
        "Issue mandatory evacuation for Zone A & B",
        "Activate emergency shelters",
        "Alert hospitals for emergency preparedness",
        "Deploy rescue boats to standby positions",
    ],
    "MODERATE": [
        "Activate primary pump stations",
        "Pre-position flood barriers at key locations",
        "Issue flood advisory to all residents",
        "Alert rescue teams to standby status",
        "Close flood-prone roads as precaution",
        "Check shelter availability and capacity",
    ],
    "LOW": [
        "Monitor water levels continuously",
        "Inspect drainage systems for blockages",
        "Issue weather advisory bulletin",
        "Verify pump station operational readiness",
    ],
    "SAFE": [
        "Routine monitoring active",
        "All systems nominal",
        "Continue standard surveillance protocol",
    ],
}


def calculate_flood_prediction(
    rainfall: float,
    humidity: float,
    wind_speed: float,
    temperature: float,
    recent_rainfall_6h: float = 0.0,
) -> dict:
    """
    Calculate flood risk metrics from real-time weather inputs.

    Scoring model:
    - Rainfall (0-40 pts):       Hourly rainfall heavily weighted
    - Cumulative rain (0-30 pts): 6-hour cumulative rainfall
    - Humidity (0-15 pts):       Above 65% starts contributing
    - Wind (0-5 pts):            Strong wind contributes marginally
    - Temperature (0-10 pts):    Cold temp + rain increases risk

    Total max probability = 100%
    Severity thresholds: SAFE < 15% | LOW 15-40% | MODERATE 40-70% | HIGH >= 70%
    """
    rainfall_score    = min(rainfall * 4.0, 40.0)
    cumulative_score  = min(recent_rainfall_6h * 1.5, 30.0)
    humidity_score    = max(0.0, (humidity - 65.0) / 35.0 * 15.0) if humidity > 65 else 0.0
    wind_score        = min(wind_speed / 100.0 * 5.0, 5.0)
    temp_score        = max(0.0, (30.0 - temperature) / 30.0 * 10.0) if temperature < 30 else 0.0

    probability = round(
        min(rainfall_score + cumulative_score + humidity_score + wind_score + temp_score, 100.0),
        1,
    )

    # Confidence: only non-zero when there is active rainfall
    has_rain = rainfall > 0 or recent_rainfall_6h > 0
    confidence = round(
        min(70.0 + rainfall * 0.5 + recent_rainfall_6h * 0.2, 98.0), 1
    ) if has_rain else 0.0

    # ── Severity thresholds ────────────────────────────────────────────────────
    if probability >= 70:
        severity = level = "HIGH"
        affected_areas = FLOOD_PRONE_AREAS["HIGH"] + FLOOD_PRONE_AREAS["MODERATE"]
        actions        = RECOMMENDED_ACTIONS["HIGH"]
    elif probability >= 40:
        severity = level = "MODERATE"
        affected_areas = FLOOD_PRONE_AREAS["MODERATE"] + FLOOD_PRONE_AREAS["LOW"]
        actions        = RECOMMENDED_ACTIONS["MODERATE"]
    elif probability >= 15:
        severity = level = "LOW"
        affected_areas = FLOOD_PRONE_AREAS["LOW"]
        actions        = RECOMMENDED_ACTIONS["LOW"]
    else:
        severity = level = "SAFE"
        affected_areas = []
        actions        = RECOMMENDED_ACTIONS["SAFE"]

    # ── Derived hydrodynamic metrics ───────────────────────────────────────────
    estimated_water_depth = round(probability / 100.0 * 4.0, 2) if probability > 0 else 0.0
    river_level           = round(probability / 100.0 * 7.0, 2) if probability > 0 else 0.0
    soil_moisture         = round(min(humidity * 0.3 + rainfall * 0.5, 100.0), 1)

    # ── Rescue resource calculation ────────────────────────────────────────────
    rescue_boats = max(0, int(probability / 20)) if probability > 0 else 0
    ambulances   = max(0, int(probability / 15)) if probability > 0 else 0
    drones       = max(0, int(probability / 25)) if probability > 0 else 0
    priority = (
        "CRITICAL" if probability >= 70 else
        "HIGH"     if probability >= 40 else
        "MEDIUM"   if probability >= 15 else
        "LOW"
    )

    # ETA minutes: 0 for LOW/SAFE, 45m for MEDIUM, 75m+ for HIGH/CRITICAL
    if priority in ("LOW", "SAFE") or level in ("LOW", "SAFE"):
        eta_minutes = 0
    elif priority == "MEDIUM" or level == "MODERATE":
        eta_minutes = round(35.0 + (probability - 15.0) * 0.5)
    else:
        eta_minutes = round(65.0 + (probability - 40.0) * 0.5)

    return {
        "probability":           probability,
        "severity":              severity,
        "level":                 level,
        "confidence":            confidence,
        "estimated_water_depth": estimated_water_depth,
        "river_level":           river_level,
        "soil_moisture":         soil_moisture,
        "affected_areas":        affected_areas,
        "recommended_actions":   actions,
        "rescue_resources": {
            "rescue_boats": rescue_boats,
            "ambulances":   ambulances,
            "drones":       drones,
            "priority":     priority,
            "eta_minutes":  eta_minutes,
        },
    }

"""
Recommendations Route
POST /api/recommendations/send  — dispatch municipal actions & send Resend email alert to likith824788@gmail.com
GET  /api/recommendations        — retrieve last N dispatched recommendations
"""
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from ..database import get_database
from ..services.alert_service import send_flood_alert, build_recommendation_email
from ..config import settings

router = APIRouter(prefix="/recommendations", tags=["Municipal Recommendations"])

# ── In-memory fallback store ──────────────────────────────────────────────────
_CACHE: List[dict] = []


class RecommendationPayload(BaseModel):
    actions:        List[str]
    severity:       str = "SAFE"
    sent_by:        str = "Municipal Decision Agent"
    probability:    float = 0.0
    location:       str = settings.DEFAULT_LOCATION_NAME
    affected_areas: List[str] = []


async def _async_send_email(doc: dict):
    """Background task to dispatch Resend email without blocking HTTP response."""
    try:
        subject = f"🏛️ HydroShield Action Recommendation Dispatched — [{doc['severity']}] {doc['location']}"
        body = build_recommendation_email(
            severity = doc["severity"],
            actions  = doc["actions"],
            location = doc["location"],
            sent_by  = doc["sent_by"],
        )
        await send_flood_alert(
            subject         = subject,
            body_html       = body,
            recipient_email = "likith824788@gmail.com",
            email_type      = "Municipal Recommendation",
        )
    except Exception as e:
        print(f"[Recommendations] Background email send error: {e}")


@router.post("/send")
async def send_recommendation(payload: RecommendationPayload):
    """Store dispatched actions to MongoDB and trigger background Resend email alert."""
    doc = {
        "id":             str(uuid.uuid4()),
        "actions":        payload.actions,
        "severity":       payload.severity,
        "sent_by":        payload.sent_by,
        "location":       payload.location,
        "probability":    payload.probability,
        "affected_areas": payload.affected_areas,
        "sent_at":        datetime.utcnow().isoformat(),
        "action_count":   len(payload.actions),
    }

    # Store in memory immediately
    _CACHE.insert(0, doc)

    # Non-blocking DB write
    try:
        db = await get_database()
        await db["recommendations"].insert_one({**doc})
    except Exception as e:
        print(f"[Recommendations] DB write skipped: {e}")

    # Dispatch email in background so HTTP response returns instantly
    asyncio.create_task(_async_send_email(doc))

    return {
        "success": True,
        "data":    doc,
        "message": f"Successfully dispatched {len(payload.actions)} action(s) to Control Room and sent email to likith824788@gmail.com",
    }


@router.get("")
async def get_recommendations(limit: int = 20):
    """Retrieve the most recent dispatched recommendations."""
    try:
        db   = await get_database()
        docs = await db["recommendations"].find({}, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(length=limit)
        return {"success": True, "data": docs, "count": len(docs)}
    except Exception as e:
        data = _CACHE[:limit]
        return {"success": True, "data": data, "count": len(data)}

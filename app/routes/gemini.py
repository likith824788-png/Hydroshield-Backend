"""
Gemini AI Routes
POST /api/gemini/civil-advice   — Civil protection recommendations
POST /api/gemini/rescue-plan    — Detailed rescue operation plan
POST /api/alerts/broadcast      — Send alert email to all civilian locality emails
"""
import asyncio
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from ..services.gemini_service import call_gemini
from ..services.alert_service import send_flood_alert, _append_log

router = APIRouter(tags=["Gemini AI"])


# ─── Civil Protection Advice ─────────────────────────────────────────────────

class CivilAdviceRequest(BaseModel):
    flood_level: str = "SAFE"
    location: str = "Unknown"
    probability: float = 0.0
    affected_areas: List[str] = []


@router.post("/gemini/civil-advice")
async def get_civil_advice(req: CivilAdviceRequest):
    """Generate AI civil protection recommendations using Gemini."""
    prompt = f"""You are an expert disaster management officer for flood response.
Current situation:
- Location: {req.location}
- Flood Level: {req.flood_level}
- Flood Probability: {req.probability:.1f}%
- Affected Areas: {', '.join(req.affected_areas) if req.affected_areas else 'None identified'}

Provide 6–8 specific, actionable civil protection recommendations for emergency response teams.
Format as a numbered list. Be concise and practical. Focus on immediate actions."""

    text = await call_gemini(prompt, expect_json=False)
    return {"success": True, "advice": text}


# ─── Rescue Mission Plan ──────────────────────────────────────────────────────

class RescuePlanRequest(BaseModel):
    priority: str = "LOW"
    flood_level: str = "SAFE"
    probability: float = 0.0
    location: str = "Unknown"
    affected_areas: List[str] = []
    affected_population: Optional[int] = None


@router.post("/gemini/rescue-plan")
async def generate_rescue_plan(req: RescuePlanRequest):
    """Generate a detailed AI rescue operation plan using Gemini."""
    prompt = f"""You are an expert flood rescue coordinator. Generate a detailed rescue operation plan.

Mission Details:
- Location: {req.location}
- Mission Priority: {req.priority}
- Flood Emergency Level: {req.flood_level}
- Flood Probability: {req.probability:.1f}%
- Affected Areas: {', '.join(req.affected_areas) if req.affected_areas else 'Unknown'}
- Estimated Affected Population: {req.affected_population or 'Unknown'}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "rescue_boats": <integer>,
  "ambulances": <integer>,
  "helicopters": <integer>,
  "drones": <integer>,
  "rescue_teams": <integer>,
  "medical_personnel": <integer>,
  "food_packets": <integer>,
  "water_bottles": <integer>,
  "life_jackets": <integer>,
  "first_aid_kits": <integer>,
  "evacuation_zones": [<string>, ...],
  "priority_actions": [<string>, ...],
  "estimated_rescue_time_hours": <number>,
  "communication_channels": [<string>, ...],
  "summary": "<brief operational summary>"
}}"""

    plan = await call_gemini(prompt, expect_json=True)
    return {"success": True, "plan": plan}


# ─── Broadcast Alert to Civilians ────────────────────────────────────────────

class BroadcastRequest(BaseModel):
    message: str
    recipients: List[str]
    location: str = "Community"


def _build_civilian_alert_email(message: str, location: str) -> str:
    return f"""
<div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #fed7aa; box-shadow: 0 4px 20px rgba(234,88,12,0.1);">
  <div style="background: linear-gradient(135deg, #ea580c, #dc2626); padding: 28px; text-align: center;">
    <h1 style="color: #ffffff; font-size: 22px; margin: 0; font-weight: 800;">
      ⚠️ Emergency Alert — {location}
    </h1>
    <p style="color: rgba(255,255,255,0.9); font-size: 12px; margin: 6px 0 0;">
      HydroShield Civil Protection System
    </p>
  </div>
  <div style="padding: 28px;">
    <div style="background: #fff7ed; border-left: 4px solid #ea580c; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
      <div style="font-size: 11px; color: #ea580c; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;">MESSAGE FROM CIVIL PROTECTION AUTHORITY</div>
      <div style="font-size: 16px; font-weight: 600; color: #0f172a; line-height: 1.6;">{message}</div>
    </div>
    <div style="font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 14px;">
      This is an automated emergency alert from HydroShield AI Flood Management System.<br/>
      Please follow instructions from local authorities. Stay safe.
    </div>
  </div>
</div>
"""


async def _send_one(recipient: str, subject: str, body: str, location: str):
    """Send a single email without logging (batch log handled separately)."""
    from ..services.alert_service import send_flood_alert
    await send_flood_alert(
        subject=subject,
        body_html=body,
        recipient_email=recipient,
        email_type="Civilian Alert",
    )


@router.post("/alerts/broadcast")
async def broadcast_alert(req: BroadcastRequest):
    """Send an emergency alert to all civilian locality emails via Resend."""
    if not req.recipients:
        return {"success": False, "error": "No recipient emails provided."}

    subject  = f"⚠️ Emergency Alert — {req.location}"
    body_html = _build_civilian_alert_email(req.message, req.location)

    # Fire all sends concurrently in background
    async def _send_all():
        tasks = [
            send_flood_alert(
                subject=subject,
                body_html=body_html,
                recipient_email=r,
                email_type="Civilian Alert",
            )
            for r in req.recipients
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.create_task(_send_all())

    return {
        "success": True,
        "message": f"Alert dispatched to {len(req.recipients)} recipient(s).",
        "recipients_count": len(req.recipients),
    }

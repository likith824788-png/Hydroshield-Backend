"""
Citizen SOS Route
POST /api/sos  — Submit emergency incident & trigger background Resend alert to likith824788@gmail.com
GET  /api/sos  — Retrieve recent SOS incidents
"""
import os
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import JSONResponse
from typing import Optional, List
from ..database import get_database
from ..services.alert_service import send_flood_alert, build_sos_alert_email

router = APIRouter(prefix="/sos", tags=["Citizen SOS"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── In-memory fallback ────────────────────────────────────────────────────────
_SOS_CACHE: List[dict] = []

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE_MB = 10


async def _async_send_sos_email(incident: dict):
    """Background task to dispatch SOS email to likith824788@gmail.com."""
    try:
        subject = f"🚨 URGENT SOS Incident Alert [{incident['id']}] — {incident['description'][:40]}..."
        email_body = build_sos_alert_email(
            incident_id = incident["id"],
            description = incident["description"],
            latitude    = incident.get("latitude"),
            longitude   = incident.get("longitude"),
            severity    = incident.get("severity", "CRITICAL"),
            contact     = incident.get("contact"),
            name        = incident.get("name"),
            image_url   = incident.get("image_url"),
        )
        await send_flood_alert(
            subject         = subject,
            body_html       = email_body,
            recipient_email = "likith824788@gmail.com",
            email_type      = "SOS Alert",
        )
    except Exception as e:
        print(f"[SOS] Background email send error: {e}")


@router.post("")
async def submit_sos(
    description:    str = Form(...),
    latitude:       Optional[float] = Form(None),
    longitude:      Optional[float] = Form(None),
    severity:       Optional[str]   = Form("CRITICAL"),
    contact:        Optional[str]   = Form(None),
    name:           Optional[str]   = Form(None),
    image:          Optional[UploadFile] = File(None),
):
    """
    Submit a citizen emergency SOS incident.
    Stores to memory and MongoDB, then dispatches background email to likith824788@gmail.com.
    Returns HTTP 201 Created instantly.
    """
    image_url = None

    if image and image.filename:
        ext = image.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"File type .{ext} not allowed."},
            )
        filename = f"{uuid.uuid4()}.{ext}"
        save_path = os.path.join(UPLOAD_DIR, filename)
        contents  = await image.read()

        if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={"success": False, "error": f"Image exceeds {MAX_FILE_SIZE_MB} MB limit."},
            )
        with open(save_path, "wb") as f:
            f.write(contents)
        image_url = f"/uploads/{filename}"

    incident_id = f"SOS-{str(uuid.uuid4())[:8].upper()}"

    incident = {
        "id":           incident_id,
        "description":  description.strip(),
        "name":         name or "Anonymous",
        "latitude":     latitude,
        "longitude":    longitude,
        "severity":     severity or "CRITICAL",
        "contact":      contact,
        "image_url":    image_url,
        "status":       "RECEIVED",
        "forwarded":    True,
        "submitted_at": datetime.utcnow().isoformat(),
        "message":      "Incident received and forwarded to Disaster Management & Email Alert System.",
    }

    # Store in memory immediately
    _SOS_CACHE.insert(0, incident)
    if len(_SOS_CACHE) > 200:
        _SOS_CACHE.pop()

    # Non-blocking DB write
    try:
        db = await get_database()
        await db["sos_incidents"].insert_one({**incident})
    except Exception as e:
        print(f"[SOS] DB write skipped: {e}")

    # Dispatch email in background task
    asyncio.create_task(_async_send_sos_email(incident))

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "data":    incident,
            "message": "Emergency SOS submitted successfully. Email alert dispatched to likith824788@gmail.com.",
        },
    )


@router.get("")
async def get_sos_incidents(limit: int = 50):
    """Retrieve the most recent SOS incident reports."""
    try:
        db        = await get_database()
        cursor    = db["sos_incidents"].find({}, {"_id": 0}).sort("submitted_at", -1).limit(limit)
        incidents = await cursor.to_list(length=limit)
        return {"success": True, "data": incidents, "count": len(incidents)}
    except Exception as e:
        data = _SOS_CACHE[:limit]
        return {"success": True, "data": data, "count": len(data)}

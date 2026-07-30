"""
Email Alert Service — Resend API dispatcher with in-memory email log for Recent Updates page.
"""
import httpx
from datetime import datetime
from ..config import settings

RESEND_API_URL = "https://api.resend.com/emails"

# ── In-memory email dispatch log for /api/updates ──────────────────────────
_EMAIL_LOG: list = []
MAX_LOG_SIZE = 200


async def send_flood_alert(
    subject: str,
    body_html: str,
    recipient_email: str = None,
    email_type: str = "General Alert",
) -> dict:
    """
    Dispatch an emergency email alert via Resend API.
    Logs every dispatch attempt to _EMAIL_LOG.
    """
    from_email = settings.RESEND_FROM_EMAIL or "onboarding@resend.dev"
    to_email   = recipient_email or settings.ALERT_RECIPIENT_EMAIL or "likith824788@gmail.com"
    log_entry  = {
        "id":         None,
        "subject":    subject,
        "recipient":  to_email,
        "type":       email_type,
        "status":     "pending",
        "sent_at":    datetime.utcnow().isoformat(),
        "error":      None,
        "body_html":  body_html,
    }

    if not settings.RESEND_API_KEY or settings.RESEND_API_KEY in ("", "your_resend_api_key_here"):
        log_entry["status"] = "failed"
        log_entry["error"]  = "Resend API key not configured"
        _append_log(log_entry)
        return {"success": False, "error": log_entry["error"]}

    payload = {
        "from":    from_email,
        "to":      [to_email],
        "subject": subject,
        "html":    body_html,
    }
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type":  "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(RESEND_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            log_entry["id"]     = data.get("id")
            log_entry["status"] = "sent"
            print(f"[AlertService] Email sent to {to_email}: ID={data.get('id')}")
            _append_log(log_entry)
            return {"success": True, "data": data}

    except httpx.HTTPStatusError as e:
        log_entry["status"] = "failed"
        log_entry["error"]  = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except httpx.TimeoutException:
        log_entry["status"] = "failed"
        log_entry["error"]  = "Request timed out"
    except Exception as e:
        log_entry["status"] = "failed"
        log_entry["error"]  = str(e)

    print(f"[AlertService] Email failed: {log_entry['error']}")
    _append_log(log_entry)
    return {"success": False, "error": log_entry["error"]}


def _append_log(entry: dict):
    """Prepend to log and cap size."""
    _EMAIL_LOG.insert(0, entry)
    if len(_EMAIL_LOG) > MAX_LOG_SIZE:
        _EMAIL_LOG.pop()


def get_email_log() -> list:
    """Return the in-memory email log (most recent first)."""
    return _EMAIL_LOG


# ─────────────────────────────────────────────────────────────────────────────


def build_recommendation_email(
    severity: str,
    actions: list,
    location: str,
    sent_by: str = "Municipal Decision Agent",
) -> str:
    """Build a styled HTML email for Municipal Decision Agent recommendations."""
    severity_color = {
        "HIGH":     "#dc2626",
        "MODERATE": "#ea580c",
        "LOW":      "#ca8a04",
        "SAFE":     "#16a34a",
    }.get(severity, "#0284c7")

    actions_html = "".join(
        f"<li style='margin:6px 0; padding:6px 12px; background:#f0f9ff; border-left:3px solid #0284c7; border-radius:4px; font-weight:600; color:#0f172a;'>{a}</li>"
        for a in actions
    ) if actions else "<li>No specific actions selected</li>"

    return f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 620px; margin: 0 auto; background: #ffffff; padding: 0; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.06);">
      <!-- Header -->
      <div style="background: linear-gradient(135deg, #1d4ed8, #0284c7); padding: 28px; text-align: center;">
        <h1 style="color: #ffffff; font-size: 24px; margin: 0; font-weight: 700; letter-spacing: 0.02em;">
          🏛️ Municipal Control Room Action Dispatch
        </h1>
        <p style="color: rgba(255,255,255,0.9); font-size: 13px; margin: 6px 0 0;">
          Issued by: {sent_by}
        </p>
      </div>

      <div style="padding: 24px;">
        <!-- Level Badge -->
        <div style="background: {severity_color}12; border-left: 4px solid {severity_color}; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em;">Emergency Severity</div>
            <div style="font-size: 22px; font-weight: 800; color: {severity_color};">{severity}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em;">Target Location</div>
            <div style="font-size: 14px; font-weight: 700; color: #0f172a;">{location}</div>
          </div>
        </div>

        <!-- Dispatched Actions -->
        <div style="margin-bottom: 20px;">
          <h3 style="font-size: 15px; color: #0f172a; margin-bottom: 10px;">Dispatched Actions ({len(actions)}):</h3>
          <ul style="list-style: none; padding: 0; margin: 0; font-size: 13px;">
            {actions_html}
          </ul>
        </div>

        <!-- Footer -->
        <div style="font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 14px; margin-top: 24px;">
          HydroShield AI Disaster Management System · Recipient: likith824788@gmail.com
        </div>
      </div>
    </div>
    """


def build_sos_alert_email(
    incident_id: str,
    description: str,
    latitude: float,
    longitude: float,
    severity: str = "HIGH",
    contact: str = None,
    name: str = None,
    image_url: str = None,
) -> str:
    """Build a styled HTML email for a Citizen SOS Emergency Report."""
    coords_text  = f"{latitude}, {longitude}" if (latitude and longitude) else "Coordinates Not Available"
    contact_text = contact if contact else "Not provided"
    name_text    = name if name else "Anonymous"

    image_html = f"""
    <div style="margin: 16px 0; text-align: center;">
      <img src="{image_url}" alt="SOS Attached Photo" style="max-width: 100%; max-height: 300px; border-radius: 8px; border: 1px solid #cbd5e1;" />
    </div>
    """ if image_url else ""

    return f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 620px; margin: 0 auto; background: #ffffff; padding: 0; border-radius: 16px; overflow: hidden; border: 1px solid #fecaca; box-shadow: 0 4px 20px rgba(220,38,38,0.1);">
      <!-- Header -->
      <div style="background: linear-gradient(135deg, #dc2626, #ea580c); padding: 28px; text-align: center;">
        <h1 style="color: #ffffff; font-size: 24px; margin: 0; font-weight: 800; letter-spacing: 0.02em;">
          🚨 URGENT: Citizen SOS Emergency Incident
        </h1>
        <p style="color: rgba(255,255,255,0.9); font-size: 13px; margin: 6px 0 0;">
          Incident ID: {incident_id}
        </p>
      </div>

      <div style="padding: 24px;">
        <!-- Emergency Box -->
        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
          <div style="font-size: 11px; color: #dc2626; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;">INCIDENT DESCRIPTION</div>
          <div style="font-size: 15px; font-weight: 600; color: #0f172a; line-height: 1.5;">{description}</div>
        </div>

        <!-- Incident Details Table -->
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px;">
          <tr style="background: #f8fafc;">
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #64748b; width: 35%;">Reporter Name</td>
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #0f172a; font-weight: 600;">{name_text}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #64748b;">Contact Number</td>
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #0f172a; font-weight: 600;">{contact_text}</td>
          </tr>
          <tr style="background: #f8fafc;">
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #64748b;">GPS Location</td>
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #0f172a; font-weight: 600;">{coords_text}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #64748b;">Severity Rating</td>
            <td style="padding: 10px 14px; border: 1px solid #e2e8f0; color: #dc2626; font-weight: 700;">{severity}</td>
          </tr>
        </table>

        {image_html}

        <!-- Footer -->
        <div style="font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 14px; margin-top: 24px;">
          Forwarded immediately to Emergency First Responders · Recipient: likith824788@gmail.com
        </div>
      </div>
    </div>
    """


def build_flood_alert_email(level: str, probability: float, location: str, affected_areas: list) -> str:
    """Build legacy flood alert body."""
    return build_recommendation_email(severity=level, actions=affected_areas, location=location)

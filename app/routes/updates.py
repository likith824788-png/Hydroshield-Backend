"""
Recent Updates Route — GET /api/updates
Returns the in-memory log of all Resend email dispatches.
"""
from fastapi import APIRouter
from ..services.alert_service import get_email_log

router = APIRouter(prefix="/updates", tags=["Recent Updates"])


@router.get("")
async def get_recent_updates(limit: int = 50):
    """Return the most recent email dispatch log entries."""
    log = get_email_log()
    return {
        "success": True,
        "data":    log[:limit],
        "count":   len(log[:limit]),
    }

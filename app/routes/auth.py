"""
Auth Routes — Register, Login, Admin Approval, User Listing.
All user data is stored in MongoDB 'users' collection.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import re

from ..database import get_database
from ..config import settings
from ..services.auth_service import (
    hash_password,
    verify_password,
    generate_token,
    build_admin_approval_request_email,
    build_admin_approval_granted_email,
    build_admin_rejection_email,
    build_user_welcome_email,
    build_admin_pending_email,
)
from ..services.alert_service import send_flood_alert

router = APIRouter(prefix="/auth", tags=["auth"])

ADMIN_EMAIL = "likith824788@gmail.com"


# ── Pydantic Models ────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: str  # "user" or "admin"


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str  # "user" or "admin"


# ── In-memory fallback store (used when MongoDB is down) ──────────────────
_IN_MEMORY_USERS: list = [
    {
        "_id": "demo-admin-1",
        "full_name": "Likith (Admin)",
        "username": "likith",
        "email": "likith824788@gmail.com",
        "password_hash": hash_password("Hydroshield"),
        "role": "admin",
        "status": "active",
        "registered_at": "2024-01-01T00:00:00",
        "approval_token": None,
    },
    {
        "_id": "demo-admin-2",
        "full_name": "Admin Control",
        "username": "admin",
        "email": "admin@gmail.com",
        "password_hash": hash_password("Hydroshield"),
        "role": "admin",
        "status": "active",
        "registered_at": "2024-01-01T00:00:00",
        "approval_token": None,
    },
    {
        "_id": "demo-user-1",
        "full_name": "Field User",
        "username": "user",
        "email": "user@gmail.com",
        "password_hash": hash_password("hydroshield@2024"),
        "role": "user",
        "status": "active",
        "registered_at": "2024-01-01T00:00:00",
        "approval_token": None,
    },
    {
        "_id": "demo-user-2",
        "full_name": "Field Operator",
        "username": "user",
        "email": "user@hydroshield.local",
        "password_hash": hash_password("hydroshield@2024"),
        "role": "user",
        "status": "active",
        "registered_at": "2024-01-01T00:00:00",
        "approval_token": None,
    }
]


async def _get_collection():
    """Return users collection or None if DB unavailable."""
    try:
        db = await get_database()
        if db is None:
            return None
        return db["users"]
    except Exception:
        return None


async def _find_user_by_email_and_role(email: str, role: str) -> Optional[dict]:
    email_clean = email.strip().lower()
    col = await _get_collection()
    if col is not None:
        try:
            user = await col.find_one({"email": email_clean, "role": role})
            return user
        except Exception:
            pass
    # Fallback
    return next((u for u in _IN_MEMORY_USERS if u.get("email", "").lower() == email_clean and u.get("role") == role), None)


async def _find_user_by_email(email: str) -> Optional[dict]:
    email_clean = email.strip().lower()
    col = await _get_collection()
    if col is not None:
        try:
            user = await col.find_one({"email": email_clean})
            return user
        except Exception:
            pass
    return next((u for u in _IN_MEMORY_USERS if u.get("email", "").lower() == email_clean), None)


async def _find_user_by_token(token: str) -> Optional[dict]:
    col = await _get_collection()
    if col is not None:
        try:
            user = await col.find_one({"approval_token": token})
            return user
        except Exception:
            pass
    return next((u for u in _IN_MEMORY_USERS if u.get("approval_token") == token), None)


async def _insert_user(user_doc: dict):
    col = await _get_collection()
    if col is not None:
        try:
            await col.insert_one(user_doc)
            return
        except Exception:
            pass
    _IN_MEMORY_USERS.append(user_doc)


async def _update_user_status(token: str, status: str):
    col = await _get_collection()
    if col is not None:
        try:
            await col.update_one(
                {"approval_token": token},
                {"$set": {"status": status, "approval_token": None, "approved_at": datetime.utcnow().isoformat()}}
            )
            return
        except Exception:
            pass
    # Fallback
    for u in _IN_MEMORY_USERS:
        if u.get("approval_token") == token:
            u["status"] = status
            u["approval_token"] = None
            u["approved_at"] = datetime.utcnow().isoformat()


async def _get_all_users() -> list:
    col = await _get_collection()
    if col is not None:
        try:
            cursor = col.find({}, {"password_hash": 0})
            users = await cursor.to_list(length=500)
            for u in users:
                u["_id"] = str(u["_id"])
            return users
        except Exception:
            pass
    return [{k: v for k, v in u.items() if k != "password_hash"} for u in _IN_MEMORY_USERS]


# ── POST /api/auth/register ───────────────────────────────────────────────
@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    # Validate role
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'.")

    # Validate email format
    email_clean = body.email.strip().lower()
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email_clean):
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    # Check password length
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    # Check email uniqueness
    existing_email = await _find_user_by_email(email_clean)
    if existing_email:
        raise HTTPException(status_code=409, detail="An account with this email address already exists.")

    # Generate display username from email
    display_username = email_clean.split("@")[0]

    # Determine status and approval_token
    status = "active" if body.role == "user" else "pending"
    approval_token = generate_token() if body.role == "admin" else None
    now = datetime.utcnow().isoformat()

    user_doc = {
        "full_name": body.full_name.strip(),
        "username": display_username,
        "email": email_clean,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "status": status,
        "registered_at": now,
        "approval_token": approval_token,
        "approved_at": now if status == "active" else None,
        "last_login": None,
    }

    await _insert_user(user_doc)

    base_url = str(request.base_url).rstrip("/")
    approve_url = f"{base_url}/api/auth/approve?token={approval_token}&action=approve"
    reject_url  = f"{base_url}/api/auth/approve?token={approval_token}&action=reject"

    if body.role == "admin":
        # 1. Email to super admin (likith824788@gmail.com) with Accept and Reject buttons
        try:
            await send_flood_alert(
                subject=f"[HydroShield] Admin Access Request from {body.full_name}",
                body_html=build_admin_approval_request_email(
                    full_name=body.full_name,
                    username=display_username,
                    email=email_clean,
                    approve_url=approve_url,
                    reject_url=reject_url,
                    registered_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                ),
                recipient_email=ADMIN_EMAIL,
                email_type="Admin Approval Request",
            )
        except Exception as e:
            print(f"[Auth] Notice — Admin approval request email error: {e}")

        # 2. Email to applicant: "Your admin request is pending"
        try:
            await send_flood_alert(
                subject="[HydroShield] Your Admin Access Request is Pending",
                body_html=build_admin_pending_email(
                    full_name=body.full_name,
                    username=display_username,
                ),
                recipient_email=email_clean,
                email_type="Admin Pending Notification",
            )
        except Exception as e:
            print(f"[Auth] Notice — Pending notification email error: {e}")

        return {
            "success": True,
            "status": "pending",
            "message": f"Admin request submitted! An approval email has been sent to the administrator ({ADMIN_EMAIL}).",
            "role": "admin",
        }

    else:
        # User: auto-approved, send welcome email
        try:
            await send_flood_alert(
                subject="[HydroShield] Welcome! Your User Account is Ready",
                body_html=build_user_welcome_email(
                    full_name=body.full_name,
                    username=display_username,
                ),
                recipient_email=email_clean,
                email_type="User Welcome",
            )
        except Exception as e:
            print(f"[Auth] Notice — Welcome email error: {e}")

        return {
            "success": True,
            "status": "active",
            "message": "Account created successfully!",
            "role": "user",
            "user": {
                "name": body.full_name,
                "username": display_username,
                "role": "user",
                "email": email_clean,
            }
        }



# ── POST /api/auth/login ──────────────────────────────────────────────────
@router.post("/login")
async def login(body: LoginRequest):
    """
    Authenticate a user or admin.
    Checks MongoDB first (falls back to in-memory store if DB is unavailable).
    Verifies password, checks account status, and updates last_login timestamp.
    """
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'.")

    email_clean = body.email.strip().lower()

    # Look up user in DB (or in-memory fallback)
    user = await _find_user_by_email_and_role(email_clean, body.role)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Verify password
    stored_hash = user.get("password_hash", "")
    if not verify_password(body.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Check account status
    status = user.get("status", "pending")
    if status == "pending":
        raise HTTPException(
            status_code=403,
            detail="Your admin account is pending approval. Please wait for the administrator to approve your request.",
        )
    if status == "rejected":
        raise HTTPException(
            status_code=403,
            detail="Your account access was rejected. Please contact the administrator.",
        )
    if status != "active":
        raise HTTPException(status_code=403, detail="Account is not active.")

    # Update last_login timestamp in DB
    now_iso = datetime.utcnow().isoformat()
    col = await _get_collection()
    if col is not None:
        try:
            await col.update_one(
                {"email": email_clean, "role": body.role},
                {"$set": {"last_login": now_iso}},
            )
        except Exception as e:
            print(f"[Auth] Warning — Could not update last_login: {e}")
    else:
        # Update in-memory fallback
        for u in _IN_MEMORY_USERS:
            if u.get("email", "").lower() == email_clean and u.get("role") == body.role:
                u["last_login"] = now_iso
                break

    # Build safe user response object
    user_obj = {
        "name": user.get("full_name", user.get("username", email_clean.split("@")[0])),
        "email": email_clean,
        "username": user.get("username", email_clean.split("@")[0]),
        "role": body.role,
        "status": "active",
    }

    return {
        "success": True,
        "message": "Login successful.",
        "user": user_obj,
    }


# ── GET /api/auth/approve ─────────────────────────────────────────────────
@router.get("/approve", response_class=HTMLResponse)
async def approve_admin(token: str, action: str = "approve"):
    user = await _find_user_by_token(token)

    if not user:
        return HTMLResponse(content=_approval_page(
            success=False,
            message="Invalid or expired approval link. This decision token has already been used or does not exist.",
        ))

    current_status = user.get("status")

    if current_status == "active":
        return HTMLResponse(content=_approval_page(
            success=True,
            message=f"This account ({user['email']}) has already been APPROVED.",
            already_done=True,
        ))

    if current_status == "rejected":
        return HTMLResponse(content=_approval_page(
            success=False,
            message=f"This account ({user['email']}) has already been REJECTED.",
            already_done=True,
        ))

    if action == "reject":
        await _update_user_status(token, "rejected")
        try:
            await send_flood_alert(
                subject="[HydroShield] Admin Access Request Status",
                body_html=build_admin_rejection_email(full_name=user["full_name"]),
                recipient_email=user["email"],
                email_type="Admin Access Rejected",
            )
        except Exception as e:
            print(f"[Auth] Notice — Rejection email sending failed: {e}")

        return HTMLResponse(content=_approval_page(
            success=False,
            name=user["full_name"],
            username=user["username"],
            email=user["email"],
            message=f"Admin request for {user['full_name']} ({user['email']}) has been REJECTED. A notification email was sent to {user['email']}.",
        ))

    else: # approve / accept
        await _update_user_status(token, "active")
        try:
            await send_flood_alert(
                subject="[HydroShield] 🎉 Your Admin Access Has Been Approved!",
                body_html=build_admin_approval_granted_email(
                    full_name=user["full_name"],
                    username=user["username"],
                ),
                recipient_email=user["email"],
                email_type="Admin Access Granted",
            )
        except Exception as e:
            print(f"[Auth] Notice — Approval granted email error: {e}")

        return HTMLResponse(content=_approval_page(
            success=True,
            name=user["full_name"],
            username=user["username"],
            email=user["email"],
            message=f"Admin access ACCEPTED for {user['full_name']} ({user['email']}). A confirmation email was sent to {user['email']}.",
        ))


# ── GET /api/auth/users ───────────────────────────────────────────────────
@router.get("/users")
async def list_users():
    """Return all registered users (admin use only — add auth middleware in production)."""
    users = await _get_all_users()
    return {"success": True, "count": len(users), "users": users}


# ── Approval HTML page ────────────────────────────────────────────────────
def _approval_page(success: bool, message: str = "", name: str = "", username: str = "", email: str = "", already_done: bool = False) -> str:
    icon = "✅" if success else "❌"
    color = "#16a34a" if success else "#dc2626"
    bg = "#f0fdf4" if success else "#fef2f2"
    border = "#bbf7d0" if success else "#fecaca"
    title = "Approved!" if (success and not already_done) else ("Already Approved" if already_done else "Invalid Token")

    details_html = f"""
    <div style="margin-top:20px;padding:16px;background:#ffffff;border-radius:10px;border:1px solid {border};text-align:left;font-size:14px;color:#374151;">
      <div><strong>Name:</strong> {name}</div>
      <div style="margin-top:6px;"><strong>Username:</strong> {username}</div>
      <div style="margin-top:6px;"><strong>Email:</strong> {email}</div>
    </div>
    """ if name else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>HydroShield — Admin Approval</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f0f9ff,#e0f2fe,#ede9fe);padding:24px}}
    .card{{max-width:480px;width:100%;background:#ffffff;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.1);overflow:hidden;border:1px solid #e2e8f0}}
    .header{{background:linear-gradient(135deg,#1d4ed8,#0284c7);padding:32px;text-align:center}}
    .header h1{{color:#fff;font-size:20px;font-weight:800;margin-top:8px}}
    .header p{{color:rgba(255,255,255,0.8);font-size:13px;margin-top:4px}}
    .body{{padding:28px}}
    .status{{background:{bg};border:1px solid {border};border-radius:14px;padding:22px;text-align:center}}
    .icon{{font-size:48px;margin-bottom:12px}}
    .status-title{{font-size:20px;font-weight:800;color:{color}}}
    .status-msg{{font-size:13px;color:#64748b;margin-top:8px;line-height:1.6}}
    .footer{{padding:16px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;text-align:center}}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div style="font-size:36px">💧</div>
      <h1>HydroShield Auth</h1>
      <p>Admin Access Management</p>
    </div>
    <div class="body">
      <div class="status">
        <div class="icon">{icon}</div>
        <div class="status-title">{title}</div>
        <div class="status-msg">{message}</div>
        {details_html}
      </div>
    </div>
    <div class="footer">HydroShield AI Disaster Management System · Admin Portal</div>
  </div>
</body>
</html>"""

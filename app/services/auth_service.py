"""
Auth Service — Password hashing, token generation, and email HTML builders.
"""
import hashlib
import hmac
import uuid
import base64
import os
from datetime import datetime, timedelta


# ── Password Hashing (pbkdf2_sha256 via passlib — no byte limit) ──────────
try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
    _USE_PASSLIB = True
except ImportError:
    _USE_PASSLIB = False


def hash_password(password: str) -> str:
    """Hash a plaintext password using pbkdf2_sha256 (no byte-length limit)."""
    if _USE_PASSLIB:
        return _pwd_context.hash(password)
    # SHA-256 fallback if passlib not installed
    salt = os.urandom(16).hex()
    h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"sha256:{salt}:{h}"


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against stored hash."""
    if _USE_PASSLIB and not hashed.startswith("sha256:"):
        try:
            return _pwd_context.verify(plain, hashed)
        except Exception:
            return False
    # SHA-256 fallback
    if hashed.startswith("sha256:"):
        parts = hashed.split(":")
        if len(parts) == 3:
            _, salt, stored_hash = parts
            h = hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest()
            return hmac.compare_digest(h, stored_hash)
    return False


# ── Token generation ───────────────────────────────────────────────────────
def generate_token() -> str:
    """Generate a secure random token."""
    return str(uuid.uuid4()).replace("-", "") + base64.urlsafe_b64encode(os.urandom(12)).decode().rstrip("=")


# ── Email HTML Builders ────────────────────────────────────────────────────

def build_admin_approval_request_email(
    full_name: str,
    username: str,
    email: str,
    approve_url: str,
    reject_url: str,
    registered_at: str,
) -> str:
    """Email sent to likith824788@gmail.com when a new admin registration is requested."""
    return f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:640px;margin:0 auto;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 4px 24px rgba(124,58,237,0.1);">
      <!-- Header -->
      <div style="background:linear-gradient(135deg,#7c3aed,#4f46e5);padding:32px 28px;text-align:center;">
        <div style="font-size:40px;margin-bottom:8px;">🛡️</div>
        <h1 style="color:#ffffff;font-size:22px;margin:0;font-weight:800;letter-spacing:0.02em;">
          Admin Access Request
        </h1>
        <p style="color:rgba(255,255,255,0.85);font-size:13px;margin:8px 0 0;">
          HydroShield — AI Flood Management System
        </p>
      </div>

      <div style="padding:28px;">
        <p style="font-size:15px;color:#374151;margin:0 0 20px;">
          A new user has requested <strong>Administrator</strong> access to the HydroShield system. Please review the details below and select <strong>Accept</strong> or <strong>Reject</strong>.
        </p>

        <!-- User Details -->
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;margin-bottom:24px;">
          <div style="padding:12px 18px;background:#ede9fe;border-bottom:1px solid #ddd6fe;">
            <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#7c3aed;">Applicant Details</span>
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <tr>
              <td style="padding:11px 18px;color:#64748b;border-bottom:1px solid #f1f5f9;width:35%;">Full Name</td>
              <td style="padding:11px 18px;color:#0f172a;font-weight:600;border-bottom:1px solid #f1f5f9;">{full_name}</td>
            </tr>
            <tr>
              <td style="padding:11px 18px;color:#64748b;border-bottom:1px solid #f1f5f9;">Username / Identifier</td>
              <td style="padding:11px 18px;color:#0f172a;font-weight:600;border-bottom:1px solid #f1f5f9;">{username}</td>
            </tr>
            <tr>
              <td style="padding:11px 18px;color:#64748b;border-bottom:1px solid #f1f5f9;">Email Address</td>
              <td style="padding:11px 18px;color:#0f172a;font-weight:600;border-bottom:1px solid #f1f5f9;">{email}</td>
            </tr>
            <tr>
              <td style="padding:11px 18px;color:#64748b;">Requested At</td>
              <td style="padding:11px 18px;color:#0f172a;font-weight:600;">{registered_at}</td>
            </tr>
          </table>
        </div>

        <!-- Action Buttons (Accept & Reject) -->
        <div style="display:flex;gap:14px;justify-content:center;margin-bottom:24px;">
          <a href="{approve_url}" style="flex:1;max-width:200px;text-align:center;background:linear-gradient(135deg,#16a34a,#15803d);color:#ffffff;text-decoration:none;padding:14px 20px;border-radius:10px;font-size:14px;font-weight:700;box-shadow:0 4px 14px rgba(22,163,74,0.35);">
            ✅ Accept Request
          </a>
          <a href="{reject_url}" style="flex:1;max-width:200px;text-align:center;background:linear-gradient(135deg,#dc2626,#b91c1c);color:#ffffff;text-decoration:none;padding:14px 20px;border-radius:10px;font-size:14px;font-weight:700;box-shadow:0 4px 14px rgba(220,38,38,0.35);">
            ❌ Reject Request
          </a>
        </div>

        <p style="font-size:12px;color:#94a3b8;text-align:center;margin:0;">
          Clicking either button will update the user status and automatically send a notification email to the applicant.
        </p>
      </div>

      <div style="padding:16px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;text-align:center;">
        HydroShield Auth System · Admin Decision Request
      </div>
    </div>
    """


def build_admin_rejection_email(full_name: str) -> str:
    """Email sent to applicant when their admin request is rejected."""
    return f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:620px;margin:0 auto;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 4px 24px rgba(220,38,38,0.1);">
      <!-- Header -->
      <div style="background:linear-gradient(135deg,#dc2626,#b91c1c);padding:32px 28px;text-align:center;">
        <div style="font-size:40px;margin-bottom:8px;">❌</div>
        <h1 style="color:#ffffff;font-size:22px;margin:0;font-weight:800;">
          Admin Request Status
        </h1>
        <p style="color:rgba(255,255,255,0.85);font-size:13px;margin:8px 0 0;">
          HydroShield — AI Flood Management System
        </p>
      </div>

      <div style="padding:28px;">
        <p style="font-size:15px;color:#374151;line-height:1.6;margin:0 0 20px;">
          Hi <strong>{full_name}</strong>, your request for <strong>Administrator</strong> access to HydroShield was not approved by the system administrator at this time.
        </p>

        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:18px;margin-bottom:24px;font-size:13px;color:#991b1b;">
          If you believe this was an error, please contact the administrator directly at <strong>likith824788@gmail.com</strong>.
        </div>
      </div>

      <div style="padding:16px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;text-align:center;">
        HydroShield AI Disaster Management System · Admin Decision
      </div>
    </div>
    """


def build_admin_approval_granted_email(full_name: str, username: str) -> str:
    """Email sent to the approved admin after approval."""
    return f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:620px;margin:0 auto;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 4px 24px rgba(22,163,74,0.1);">
      <!-- Header -->
      <div style="background:linear-gradient(135deg,#16a34a,#15803d);padding:32px 28px;text-align:center;">
        <div style="font-size:40px;margin-bottom:8px;">🎉</div>
        <h1 style="color:#ffffff;font-size:22px;margin:0;font-weight:800;">
          Admin Access Approved!
        </h1>
        <p style="color:rgba(255,255,255,0.85);font-size:13px;margin:8px 0 0;">
          HydroShield — AI Flood Management System
        </p>
      </div>

      <div style="padding:28px;">
        <p style="font-size:15px;color:#374151;line-height:1.6;margin:0 0 20px;">
          Hi <strong>{full_name}</strong>, your request for <strong>Administrator</strong> access to HydroShield has been <span style="color:#16a34a;font-weight:700;">approved</span>! 🚀
        </p>

        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:18px;margin-bottom:24px;">
          <div style="font-size:13px;color:#374151;margin-bottom:10px;font-weight:600;">Your Login Credentials:</div>
          <div style="font-size:14px;color:#0f172a;"><span style="color:#64748b;">Username:</span> <strong>{username}</strong></div>
          <div style="font-size:13px;color:#64748b;margin-top:8px;">Use the password you set during registration.</div>
        </div>

        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:14px 18px;margin-bottom:24px;font-size:13px;color:#92400e;">
          ⚠️ Keep your admin credentials secure. Do not share your password with anyone.
        </div>

        <p style="font-size:13px;color:#64748b;margin:0;">
          You now have full access to Municipal Decisions, Mission Reports, Rescue Planner, and all admin controls.
        </p>
      </div>

      <div style="padding:16px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;text-align:center;">
        HydroShield AI Disaster Management System · Admin Access Granted
      </div>
    </div>
    """


def build_user_welcome_email(full_name: str, username: str) -> str:
    """Welcome email sent to a newly registered User."""
    return f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:620px;margin:0 auto;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 4px 24px rgba(29,78,216,0.1);">
      <!-- Header -->
      <div style="background:linear-gradient(135deg,#1d4ed8,#0284c7);padding:32px 28px;text-align:center;">
        <div style="font-size:40px;margin-bottom:8px;">💧</div>
        <h1 style="color:#ffffff;font-size:22px;margin:0;font-weight:800;">
          Welcome to HydroShield!
        </h1>
        <p style="color:rgba(255,255,255,0.85);font-size:13px;margin:8px 0 0;">
          AI Flood Management System — User Portal
        </p>
      </div>

      <div style="padding:28px;">
        <p style="font-size:15px;color:#374151;line-height:1.6;margin:0 0 20px;">
          Hi <strong>{full_name}</strong>, your User account has been created successfully! You can now log in and start monitoring flood conditions.
        </p>

        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:18px;margin-bottom:24px;">
          <div style="font-size:13px;color:#374151;margin-bottom:10px;font-weight:600;">Your Login Details:</div>
          <div style="font-size:14px;color:#0f172a;"><span style="color:#64748b;">Username:</span> <strong>{username}</strong></div>
          <div style="font-size:13px;color:#64748b;margin-top:8px;">Use the password you set during registration.</div>
        </div>

        <div style="font-size:13px;color:#374151;margin-bottom:16px;font-weight:600;">What you can access:</div>
        <ul style="list-style:none;padding:0;margin:0 0 24px;display:flex;flex-direction:column;gap:8px;font-size:13px;color:#374151;">
          <li style="padding:8px 14px;background:#f8fafc;border-radius:8px;border-left:3px solid #0284c7;">📊 Live Flood Monitoring Dashboard</li>
          <li style="padding:8px 14px;background:#f8fafc;border-radius:8px;border-left:3px solid #0284c7;">🗺️ India Flood Risk Map</li>
          <li style="padding:8px 14px;background:#f8fafc;border-radius:8px;border-left:3px solid #0284c7;">🚨 Citizen SOS Reports</li>
          <li style="padding:8px 14px;background:#f8fafc;border-radius:8px;border-left:3px solid #0284c7;">🤖 AI Agent Status</li>
        </ul>

        <p style="font-size:12px;color:#94a3b8;margin:0;">
          If you did not create this account, please ignore this email.
        </p>
      </div>

      <div style="padding:16px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;text-align:center;">
        HydroShield AI Disaster Management System · User Portal
      </div>
    </div>
    """


def build_admin_pending_email(full_name: str, username: str) -> str:
    """Email sent to admin applicant telling them their request is pending."""
    return f"""
    <div style="font-family:'Inter',Arial,sans-serif;max-width:620px;margin:0 auto;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 4px 24px rgba(124,58,237,0.1);">
      <div style="background:linear-gradient(135deg,#7c3aed,#4f46e5);padding:32px 28px;text-align:center;">
        <div style="font-size:40px;margin-bottom:8px;">⏳</div>
        <h1 style="color:#ffffff;font-size:22px;margin:0;font-weight:800;">
          Admin Request Received
        </h1>
        <p style="color:rgba(255,255,255,0.85);font-size:13px;margin:8px 0 0;">
          HydroShield — AI Flood Management System
        </p>
      </div>
      <div style="padding:28px;">
        <p style="font-size:15px;color:#374151;line-height:1.6;margin:0 0 20px;">
          Hi <strong>{full_name}</strong>, your request for <strong>Administrator</strong> access to HydroShield has been received and is <strong>pending approval</strong>.
        </p>
        <div style="background:#faf5ff;border:1px solid #e9d5ff;border-radius:12px;padding:18px;margin-bottom:20px;font-size:13px;color:#374151;">
          <strong>Username:</strong> {username}<br/>
          <span style="color:#64748b;font-size:12px;margin-top:6px;display:block;">The system administrator will review your request. You'll receive another email once a decision is made.</span>
        </div>
        <p style="font-size:12px;color:#94a3b8;margin:0;">
          If you did not make this request, please ignore this email.
        </p>
      </div>
      <div style="padding:16px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;text-align:center;">
        HydroShield Auth System · Admin Access Request
      </div>
    </div>
    """

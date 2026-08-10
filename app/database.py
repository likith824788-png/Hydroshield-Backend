import certifi
import ssl
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings


class Database:
    client: AsyncIOMotorClient = None
    _connected: bool = False


db = Database()


async def get_database():
    """Return active MongoDB database instance, or None if unavailable."""
    if db.client is None:
        await connect_db()
    if db.client is None or not db._connected:
        return None
    return db.client[settings.DATABASE_NAME]


async def _try_connect(url: str, **kwargs) -> bool:
    """Attempt a single connection strategy. Returns True on success."""
    try:
        client = AsyncIOMotorClient(url, **kwargs)
        await client.admin.command("ping")
        db.client = client
        db._connected = True
        return True
    except Exception as e:
        print(f"[Database] Strategy failed: {type(e).__name__}: {str(e)[:120]}")
        try:
            client.close()
        except Exception:
            pass
        return False


async def connect_db():
    """
    Connect to MongoDB Atlas with multiple SSL fallback strategies.

    Strategy order:
      1. certifi CA bundle (recommended, most secure)
      2. tlsInsecure=True  (skip all TLS validation — fixes most SSL handshake errors)
      3. No TLS parameters  (plain connection — last resort)
    """
    is_atlas = "mongodb+srv" in settings.MONGODB_URL or "@cluster" in settings.MONGODB_URL

    base_timeouts = {
        "serverSelectionTimeoutMS": 8000,
        "connectTimeoutMS": 8000,
        "socketTimeoutMS": 10000,
    }

    host_display = (
        settings.MONGODB_URL.split("@")[-1].split("/")[0]
        if "@" in settings.MONGODB_URL
        else settings.MONGODB_URL
    )

    if is_atlas:
        strategies = [
            # ── Strategy 1: certifi CA (standard) ────────────────────────────
            {
                **base_timeouts,
                "tls": True,
                "tlsCAFile": certifi.where(),
                "tlsAllowInvalidCertificates": False,
            },
            # ── Strategy 2: tlsInsecure — bypasses all TLS validation ─────────
            # Fixes TLSV1_ALERT_INTERNAL_ERROR caused by cipher/version mismatch
            {
                **base_timeouts,
                "tls": True,
                "tlsInsecure": True,
            },
            # ── Strategy 3: Allow invalid certs + insecure ────────────────────
            {
                **base_timeouts,
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "tlsAllowInvalidHostnames": True,
            },
        ]

        print(f"[Database] Connecting to MongoDB Atlas: {host_display}")
        for i, kwargs in enumerate(strategies, 1):
            print(f"[Database] Trying SSL strategy {i}/3...")
            if await _try_connect(settings.MONGODB_URL, **kwargs):
                print(f"[Database] [OK] Connected via strategy {i}: {host_display}")
                return

        # All strategies failed
        db._connected = False
        db.client = None
        print(
            "[Database] [!] Could not connect to MongoDB Atlas after 3 SSL strategies.\n"
            "[Database] -> Your public IP is likely not whitelisted in MongoDB Atlas.\n"
            "[Database] -> Fix: Atlas Dashboard -> Network Access -> Add IP Address -> 0.0.0.0/0\n"
            "[Database] -> Using in-memory store as fallback."
        )

    else:
        # Local MongoDB — no SSL needed
        print(f"[Database] Connecting to local MongoDB: {host_display}")
        if await _try_connect(settings.MONGODB_URL, **base_timeouts):
            print("[Database] [OK] Connected to local MongoDB.")
        else:
            db._connected = False
            db.client = None
            print("[Database] [!] Could not connect to local MongoDB. Using in-memory store.")


async def close_db():
    """Safely close MongoDB client."""
    if db.client:
        try:
            db.client.close()
            db._connected = False
            print("[Database] Disconnected from MongoDB.")
        except Exception:
            pass

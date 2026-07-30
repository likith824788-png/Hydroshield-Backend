import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings


class Database:
    client: AsyncIOMotorClient = None
    _connected: bool = False


db = Database()


async def get_database():
    """Return active MongoDB database instance."""
    if db.client is None:
        await connect_db()
    return db.client[settings.DATABASE_NAME]


async def connect_db():
    """Connect to MongoDB with certifi SSL CA and fast 2s timeout fallback."""
    is_atlas = "mongodb+srv" in settings.MONGODB_URL or "@cluster" in settings.MONGODB_URL

    kwargs = {
        "serverSelectionTimeoutMS": 2500,
        "connectTimeoutMS": 2500,
        "socketTimeoutMS": 2500,
    }

    if is_atlas:
        kwargs["tls"] = True
        kwargs["tlsCAFile"] = certifi.where()
        kwargs["tlsAllowInvalidCertificates"] = True

    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URL, **kwargs)
        # Ping check
        await db.client.admin.command("ping")
        db._connected = True
        host = settings.MONGODB_URL.split("@")[-1].split("/")[0] if "@" in settings.MONGODB_URL else settings.MONGODB_URL
        print(f"[Database] Connected to MongoDB Atlas: {host}")

    except Exception as e:
        db._connected = False
        print(f"[Database] Warning — Could not connect to MongoDB ({e}). Using in-memory store.")


async def close_db():
    """Safely close client."""
    if db.client:
        try:
            db.client.close()
            db._connected = False
            print("[Database] Disconnected from MongoDB.")
        except Exception:
            pass

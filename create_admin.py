"""
Script to directly seed an active Admin user into MongoDB.
"""
import asyncio
from datetime import datetime
from app.database import get_database, connect_db, close_db
from app.services.auth_service import hash_password

ADMIN_ACCOUNTS = [
    {
        "full_name": "Likith (Administrator)",
        "username": "likith",
        "email": "likith824788@gmail.com",
        "password_hash": hash_password("Hydroshield"),
        "role": "admin",
        "status": "active",
        "registered_at": datetime.utcnow().isoformat(),
        "approval_token": None,
        "approved_at": datetime.utcnow().isoformat(),
        "last_login": None,
    },
    {
        "full_name": "System Administrator",
        "username": "admin",
        "email": "admin@gmail.com",
        "password_hash": hash_password("hydroshield@admin"),
        "role": "admin",
        "status": "active",
        "registered_at": datetime.utcnow().isoformat(),
        "approval_token": None,
        "approved_at": datetime.utcnow().isoformat(),
        "last_login": None,
    },
    {
        "full_name": "Field User",
        "username": "user",
        "email": "user@gmail.com",
        "password_hash": hash_password("hydroshield@2024"),
        "role": "user",
        "status": "active",
        "registered_at": datetime.utcnow().isoformat(),
        "approval_token": None,
        "approved_at": datetime.utcnow().isoformat(),
        "last_login": None,
    }
]


async def seed():
    print("[Seed] Connecting to database...")
    await connect_db()
    db = await get_database()

    if db is None:
        print("[Seed] Warning: MongoDB not connected. In-memory demo admin is active.")
        return

    col = db["users"]
    for acc in ADMIN_ACCOUNTS:
        result = await col.update_one(
            {"email": acc["email"], "role": acc["role"]},
            {"$set": acc},
            upsert=True
        )
        if result.upserted_id:
            print(f"✅ Created {acc['role']} account: {acc['email']}")
        else:
            print(f"🔄 Updated {acc['role']} account to active: {acc['email']}")

    await close_db()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(seed())

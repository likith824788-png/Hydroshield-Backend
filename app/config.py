from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    # ── MongoDB Atlas ──────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "hydroshield"

    # ── OpenWeather API ────────────────────────────────────
    OPENWEATHER_API_KEY: str = ""
    OPENWEATHER_URL: str = "https://api.openweathermap.org/data/2.5/weather"

    # ── Default Location (Chennai) ─────────────────────────
    DEFAULT_LATITUDE: float = 13.0827
    DEFAULT_LONGITUDE: float = 80.2707
    DEFAULT_LOCATION_NAME: str = "Chennai, India"

    # ── CORS ───────────────────────────────────────────────
    CORS_ORIGINS: Union[List[str], str] = [
        "*",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]

    # ── Resend Email Alert API ─────────────────────────────────────────────
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    ALERT_RECIPIENT_EMAIL: str = ""

    # ── Auth ───────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    JWT_SECRET: str = "hydroshield-secret-change-in-production"

    # ── Google Gemini API ──────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemma-2-27b-it"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

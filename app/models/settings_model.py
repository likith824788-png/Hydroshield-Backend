"""
AppSettings Pydantic model — used for API request/response validation on the settings route.
"""
from pydantic import BaseModel
from typing import Optional


class AppSettings(BaseModel):
    latitude:                  float  = 13.0827
    longitude:                 float  = 80.2707
    location_name:             str    = "Chennai, India"
    api_base_url:              str    = "http://localhost:8000/api"
    openweather_api_key:       str    = ""
    resend_api_key:            str    = ""
    resend_from_email:         str    = ""
    enable_email_notifications: bool  = False
    enable_citizen_alerts:     bool   = False
    alert_recipient_email:     str    = ""
    refresh_interval_seconds:  int    = 30

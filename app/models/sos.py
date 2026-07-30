from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SOSIncident(BaseModel):
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_url: Optional[str] = None
    status: str = "RECEIVED"
    forwarded: bool = True
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class SOSResponse(BaseModel):
    id: str
    description: str
    latitude: Optional[float]
    longitude: Optional[float]
    image_url: Optional[str]
    status: str
    forwarded: bool
    submitted_at: datetime
    message: str = "Incident received and forwarded to Disaster Management Team"

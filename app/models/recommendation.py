from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    actions: List[str]
    severity: str
    location: str = "Municipal Disaster Control Room"
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    sent_by: str = "Municipal Decision Agent"
    status: str = "SENT"


class RecommendationResponse(BaseModel):
    id: str
    actions: List[str]
    severity: str
    location: str
    sent_at: datetime
    status: str
    message: str = "Recommendation successfully sent to Municipal Disaster Control Room"

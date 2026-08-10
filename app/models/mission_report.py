from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class MissionReport(BaseModel):
    flood_probability: float
    affected_areas: List[str]
    resources_allocated: dict
    hospitals_assigned: List[str] = ["City General Hospital", "Metro Medical Center"]
    shelters_assigned: List[str] = ["Community Hall Alpha", "Sports Complex B", "School Zone C"]
    emergency_level: str
    mission_status: str = "ACTIVE"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    location: str = "Chennai, India"

"""
Pydantic schemas for request payloads and API responses.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatPayload(BaseModel):
    """Payload sent by the frontend chat client."""
    session_id: str = Field(..., description="Unique browser/device session identifier (UUID).")
    user_id: str = Field(default="DEMO_YOUNGPRO_001", description="Persona identifier (e.g. DEMO_YOUNGPRO_001).")
    message: str = Field(..., description="User message or query.")


class PersonaCard(BaseModel):
    """Summary card schema for displaying the 4 demo profiles on the frontend."""
    user_id: str
    category: str
    name: str
    age: int
    occupation: str
    location: str
    life_stage: str
    risk_profile: str
    income_bracket: str
    avatar_url: str
    tags: List[str]
    highlights: Dict[str, Any]

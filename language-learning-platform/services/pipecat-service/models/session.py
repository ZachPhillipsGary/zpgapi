"""Session models."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict


class SessionCreate(BaseModel):
    """Request model for creating a tutoring session."""
    user_id: str
    language_id: str
    concept_id: Optional[str] = None
    session_type: str = "conversation"  # conversation, pronunciation, grammar_practice


class SessionResponse(BaseModel):
    """Response model for session creation."""
    id: str
    user_id: str
    language_id: str
    concept_id: Optional[str]
    session_type: str
    started_at: datetime
    status: str = "active"


class TutoringSession(BaseModel):
    """Full tutoring session model."""
    id: str
    user_id: str
    language_id: str
    concept_id: Optional[str] = None
    session_type: str
    language_code: str

    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0

    transcript: List[Dict] = []
    feedback: Optional[Dict] = None

    status: str = "active"

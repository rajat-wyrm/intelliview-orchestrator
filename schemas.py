from datetime import datetime
from pydantic import BaseModel, EmailStr


class Webhook(BaseModel):
    event_id: str
    email: EmailStr
    event: str
    timestamp: datetime


class EventResponse(BaseModel):
    event_id: str
    email: EmailStr
    event: str
    timestamp: datetime

    class Config:
        from_attributes = True   # If using Pydantic v2
        # orm_mode = True         # Uncomment this instead if using Pydantic v1
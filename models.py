from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
Base = declarative_base()

class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    email = Column(String)
    event = Column(String)
    timestamp = Column(DateTime)
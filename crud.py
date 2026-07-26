from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from models import EmailEvent
from datetime import datetime
from models import EmailEvent

VALID_EVENTS = [
    "sent",
    "delivered",
    "opened",
    "clicked",
    "bounced"
]


def event_exists(db: Session, event_id: str):
    return db.query(EmailEvent).filter(
        EmailEvent.event_id == event_id
    ).first()


def create_event(db: Session, data):

    event = EmailEvent(
        event_id=data.event_id,
        email=data.email,
        event=data.event.lower(),
        timestamp=data.timestamp
    )

    try:
        db.add(event)
        db.commit()
        db.refresh(event)

    except IntegrityError:
        db.rollback()
        raise

    return event
def get_events(
    db: Session,
    event: str = None,
    skip: int = 0,
    limit: int = 10
):
    query = db.query(EmailEvent)

    if event:
        query = query.filter(
            func.lower(EmailEvent.event) == event.lower()
        )

    return query.offset(skip).limit(limit).all()
def count_events(
    db: Session,
    event_name: str,
    start_date=None,
    end_date=None
):

    query = db.query(EmailEvent).filter(
        func.lower(EmailEvent.event) == event_name.lower()
    )

    if start_date:
        query = query.filter(
            EmailEvent.timestamp >= start_date
        )

    if end_date:
        query = query.filter(
            EmailEvent.timestamp <= end_date
        )

    return query.count()

def total_events(db: Session):

    return db.query(EmailEvent).count()
from datetime import datetime

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import WEBHOOK_SECRET
from crud import (
        VALID_EVENTS,
        count_events,
        create_event,
        event_exists,
        get_events,
)
from database import engine, get_db
from models import Base
from schemas import EventResponse, Webhook


class Config:
        from_attributes = True


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Delivery Analytics API")



@app.get(
    "/events",
    response_model=list[EventResponse]
)
def list_events(
    event: str | None = None,
    page: int = 1,
    limit: int = 10,
    x_webhook_secret: str = Header(..., alias="X-Webhook-Secret"),
    db: Session = Depends(get_db)
):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook secret"
        )

    skip = (page - 1) * limit

    return get_events(
        db=db,
        event=event,
        skip=skip,
        limit=limit
    )

@app.post("/webhook")
def receive_webhook(
    data: Webhook,
    db: Session = Depends(get_db),
    x_webhook_secret: str = Header(
        ...,
        alias="X-Webhook-Secret"
    )
):

    # Authenticate webhook
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook secret"
        )

    # Validate event
    if data.event.lower() not in VALID_EVENTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid event type"
        )

    # Duplicate check
    if event_exists(db, data.event_id):
        raise HTTPException(
            status_code=400,
            detail="Duplicate Event"
        )

    # Save event
    try:
        create_event(db, data)

    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Duplicate Event"
        )

    return {
        "message": "Webhook stored successfully"
    }


@app.get("/analytics")
def analytics(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db)
):

    email_sent = count_events(db, "sent", start_date, end_date)
    delivered = count_events(db, "delivered", start_date, end_date)
    opened = count_events(db, "opened", start_date, end_date)
    clicked = count_events(db, "clicked", start_date, end_date)
    bounced = count_events(db, "bounced", start_date, end_date)

    if email_sent == 0:
        delivery_rate = 0
        open_rate = 0
        click_rate = 0
        bounce_rate = 0
    else:
        delivery_rate = round((delivered / email_sent) * 100, 2)
        open_rate = round((opened / delivered) * 100, 2) if delivered else 0
        click_rate = round((clicked / opened) * 100, 2) if opened else 0
        bounce_rate = round((bounced / email_sent) * 100, 2)

    return {
        "email_sent": email_sent,
        "delivered": delivered,
        "delivery_rate": f"{delivery_rate}%",
        "opened": opened,
        "open_rate": f"{open_rate}%",
        "clicked": clicked,
        "click_rate": f"{click_rate}%",
        "bounced": bounced,
        "bounce_rate": f"{bounce_rate}%"
    }

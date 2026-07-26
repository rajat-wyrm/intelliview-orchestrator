# Delivery Analytics API

A FastAPI-based webhook analytics service that receives email delivery events, stores them in SQLite using SQLAlchemy, and exposes analytics through a REST API.

---

## Features

- Receive email webhook events
- Store events in SQLite database
- Delivery analytics endpoint
- Duplicate event detection
- Event normalization (case-insensitive)
- Automated regression tests using Pytest
- FastAPI interactive Swagger documentation

---

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Pytest
- Uvicorn

---

## Project Structure

```
Delivery_Analytics/
│
├── app.py
├── crud.py
├── database.py
├── models.py
├── schemas.py
├── generate_data.py
├── requirements.txt
├── README.md
├── delivery.db
└── tests/
    └── test_app.py
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/nandithasri2006/Delivery_Analytics.git
```

Go into the project

```bash
cd Delivery_Analytics
```

Create virtual environment

```bash
python -m venv venv
```

Activate

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
uvicorn app:app --reload
```

Open Swagger UI

```
http://127.0.0.1:8000/docs
```

---

## API Endpoints

### GET /

Returns welcome message.

---

### POST /webhook

Stores an email webhook event.

Example

```json
{
  "event_id": "evt101",
  "email": "user@example.com",
  "event": "Delivered",
  "timestamp": "2026-07-10T10:00:00"
}
```

Response

```json
{
  "message": "Webhook stored successfully"
}
```

---

### GET /analytics

Returns analytics including

- Sent
- Delivered
- Opened
- Clicked
- Bounced
- Delivery Rate
- Open Rate
- Click Rate
- Bounce Rate

Example

```json
{
  "email_sent": 200,
  "delivered": 196,
  "delivery_rate": "98.0%",
  "opened": 150,
  "open_rate": "76.53%",
  "clicked": 90,
  "click_rate": "60.0%",
  "bounced": 4,
  "bounce_rate": "2.0%"
}
```

---

# Reliability Improvements

## Event Normalization

Webhook events are normalized to lowercase before storage.

Example

Incoming

```json
{
    "event":"Delivered"
}
```

Stored

```
delivered
```

This ensures analytics remain accurate regardless of input casing.

---

## Case-insensitive Analytics

Analytics queries perform case-insensitive comparisons to avoid silent undercounting caused by inconsistent event casing.

---

## Duplicate Event Protection

Duplicate webhook deliveries are detected using the unique `event_id`.

Duplicate requests return

```
400 Bad Request
```

with

```json
{
    "detail":"Duplicate Event"
}
```

---

## Database Session Management

Database sessions are managed using FastAPI dependency injection (`Depends(get_db)`), ensuring sessions are always closed even if an exception occurs during request handling.

---

## Testing

Run tests

```bash
python -m pytest
```

Regression test included

- Mixed-case event ("Delivered") is counted correctly.
- Duplicate event detection.
- Invalid event rejection.

---

## Current Database

SQLite

```
delivery.db
```

---

## Future Improvements

The following enhancements are planned:

- Email validation using `EmailStr`
- Timestamp validation using `datetime`
- Webhook authentication (shared secret / HMAC)
- Date range filtering for `/analytics`
- GET `/events` endpoint with pagination
- PostgreSQL support through `DATABASE_URL`
- Concurrency tests for duplicate webhook handling
- Alembic database migrations

---

## Author

**Nandhitha Sri Maraka**

GitHub

https://github.com/nandithasri2006

LinkedIn

https://www.linkedin.com/in/nandhitha-maraka-905678293/

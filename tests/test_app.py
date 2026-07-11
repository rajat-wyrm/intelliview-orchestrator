import uuid
from fastapi.testclient import TestClient
from app import app
from concurrent.futures import ThreadPoolExecutor
client = TestClient(app)

HEADERS = {
    "X-Webhook-Secret": "my-secret-key-123"  # replace with your secret
}


def test_valid_webhook():

    payload = {
        "event_id": str(uuid.uuid4()),
        "email": "user@gmail.com",
        "event": "sent",
        "timestamp": "2026-07-11T10:00:00"
    }

    response = client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )

    assert response.status_code == 200


def test_invalid_event():

    payload = {
        "event_id": str(uuid.uuid4()),
        "email": "user@gmail.com",
        "event": "invalid",
        "timestamp": "2026-07-11T10:00:00"
    }

    response = client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )

    assert response.status_code == 400


def test_duplicate_event():

    payload = {
        "event_id": str(uuid.uuid4()),
        "email": "user@gmail.com",
        "event": "sent",
        "timestamp": "2026-07-11T10:00:00"
    }

    first = client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )

    second = client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )

    assert first.status_code == 200
    assert second.status_code == 400


def test_mixed_case_event():

    payload = {
        "event_id": str(uuid.uuid4()),
        "email": "user@gmail.com",
        "event": "Delivered",
        "timestamp": "2026-07-11T10:00:00"
    }

    client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )

    analytics = client.get("/analytics")

    assert analytics.status_code == 200
    assert analytics.json()["delivered"] >= 1


def test_invalid_email():

    payload = {
        "event_id": str(uuid.uuid4()),
        "email": "not-email",
        "event": "sent",
        "timestamp": "2026-07-11T10:00:00"
    }

    response = client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )

    assert response.status_code == 422


def test_invalid_timestamp():

    payload = {
        "event_id": str(uuid.uuid4()),
        "email": "user@gmail.com",
        "event": "sent",
        "timestamp": "wrong-date"
    }

    response = client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )

    assert response.status_code == 422
def send_request(payload):
    return client.post(
        "/webhook",
        json=payload,
        headers=HEADERS
    )


def test_concurrent_duplicate_webhook():

    payload = {
        "event_id": str(uuid.uuid4()),
        "email": "user@gmail.com",
        "event": "sent",
        "timestamp": "2026-07-11T10:00:00"
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(send_request, payload)
        future2 = executor.submit(send_request, payload)

        response1 = future1.result()
        response2 = future2.result()

    status_codes = sorted(
        [response1.status_code, response2.status_code]
    )

    assert status_codes == [200, 400]
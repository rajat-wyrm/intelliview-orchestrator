import requests

URL = "http://127.0.0.1:8000/webhook"

event_id = 1

def send_events(event_name, count):
    global event_id

    for i in range(count):

        data = {
            "event_id": str(event_id),
            "email": f"user{i}@gmail.com",
            "event": event_name,
            "timestamp": "2026-06-26 10:00:00"
        }

        requests.post(URL, json=data)

        event_id += 1


send_events("sent", 200)
send_events("delivered", 195)
send_events("opened", 140)
send_events("clicked", 80)
send_events("bounced", 5)

print("Data inserted successfully.")
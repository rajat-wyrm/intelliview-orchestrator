import datetime

from deduplication import generate_idempotency_key
from storage import get_timestamp, notification_exists, save_notification

print("===== Notification Deduplication System =====")

while True:

    # Event Name Validation
    event = input("\nEnter Event Name: ").strip()
    if not event:
        print("Error: Event Name cannot be empty.")
        continue

    # User ID Validation
    user = input("Enter User ID: ").strip()
    if not user:
        print("Error: User ID cannot be empty.")
        continue

    # Timestamp Input
    timestamp = input("Enter Timestamp (Leave empty for current time): ").strip()

    if timestamp == "":
        timestamp = datetime.datetime.now().isoformat()

    # Generate Idempotency Key
    key = generate_idempotency_key(event, user)

    # Check for Duplicate Notification
    if notification_exists(key):

        print("\nNotification Skipped")

        print({
            "idempotency_key": key,
            "status": "skipped_duplicate",
            "original_sent_at": get_timestamp(key)
        })

    else:

        save_notification(key, timestamp)

        print("\nNotification Sent Successfully")

        print({
            "idempotency_key": key,
            "status": "sent",
            "sent_at": timestamp
        })

    # Continue or Exit
    choice = input("\nSend another notification? (y/n): ").strip().lower()

    if choice != 'y':
        print("\nExiting Notification Deduplication System.")
        break

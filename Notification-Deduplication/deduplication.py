import hashlib


def generate_idempotency_key(event, user):
    """
    Generates a SHA-256 hash based ONLY on event and user.
    We removed 'timestamp' to ensure that duplicate notifications
    are caught even if they arrive at different times.
    """
    # Create a unique string combining the event and user
    data = f"{event}:{user}"

    # Return the hex hash of that string
    return "sha256:" + hashlib.sha256(data.encode()).hexdigest()

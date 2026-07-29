# storage.py

notification_store = {}


def save_notification(key, timestamp):
    notification_store[key] = timestamp


def notification_exists(key):
    return key in notification_store


def get_timestamp(key):
    return notification_store.get(key)

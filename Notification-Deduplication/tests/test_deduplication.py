from deduplication import generate_idempotency_key


def test_same_event_and_user_generate_same_key():
    key1 = generate_idempotency_key("Interview Scheduled", "101")
    key2 = generate_idempotency_key("Interview Scheduled", "101")

    assert key1 == key2


def test_different_events_generate_different_keys():
    key1 = generate_idempotency_key("Interview Scheduled", "101")
    key2 = generate_idempotency_key("Interview Cancelled", "101")

    assert key1 != key2


def test_different_users_generate_different_keys():
    key1 = generate_idempotency_key("Interview Scheduled", "101")
    key2 = generate_idempotency_key("Interview Scheduled", "102")

    assert key1 != key2

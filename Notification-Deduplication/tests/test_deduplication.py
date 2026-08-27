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


# --- New edge-case coverage (Issue #9) ---


def test_exact_duplicate_repeated_calls_produce_same_key():
    """Exact-duplicate pair: identical (event, user) called multiple times
    must always collapse to the same idempotency key."""
    keys = [generate_idempotency_key("Interview Completed", "555") for _ in range(3)]

    assert len(set(keys)) == 1


def test_near_duplicate_case_difference_generates_different_key():
    """Near-duplicate pair: same words, different case. The hash is exact-
    match only (no normalization), so these must NOT collide."""
    key1 = generate_idempotency_key("Interview Scheduled", "101")
    key2 = generate_idempotency_key("interview scheduled", "101")

    assert key1 != key2


def test_near_duplicate_trailing_whitespace_generates_different_key():
    """Near-duplicate pair: same text plus trailing whitespace should also
    be treated as a distinct notification, not caught as a duplicate."""
    key1 = generate_idempotency_key("Interview Scheduled", "101")
    key2 = generate_idempotency_key("Interview Scheduled ", "101")

    assert key1 != key2


def test_non_duplicate_completely_different_event_and_user():
    """Non-duplicate pair: unrelated event and user should produce a
    completely different key."""
    key1 = generate_idempotency_key("Interview Scheduled", "101")
    key2 = generate_idempotency_key("Offer Extended", "999")

    assert key1 != key2

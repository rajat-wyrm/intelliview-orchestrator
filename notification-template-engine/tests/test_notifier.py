import logging

import pytest
from notifier import ConsoleNotifier, Notifier, TransientNotificationError


def test_notifier_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Notifier()


def test_console_notifier_delivers_message(capsys):
    notifier = ConsoleNotifier()

    notifier.deliver("alex@gmail.com", "Hello Alex")

    output = capsys.readouterr().out

    assert "alex@gmail.com" in output
    assert "Hello Alex" in output


def test_console_notifier_invalid_init_parameters():
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        ConsoleNotifier(max_attempts=0)

    with pytest.raises(ValueError, match="base_delay cannot be negative"):
        ConsoleNotifier(base_delay=-1)

    with pytest.raises(ValueError, match=r"jitter must be between 0\.0 and 0\.5"):
        ConsoleNotifier(jitter=0.6)


def test_console_notifier_rejects_empty_recipient():
    notifier = ConsoleNotifier()

    with pytest.raises(ValueError, match="Recipient cannot be empty"):
        notifier.deliver("", "Hello Alex")


def test_console_notifier_rejects_empty_message():
    notifier = ConsoleNotifier()

    with pytest.raises(ValueError, match="Message cannot be empty"):
        notifier.deliver("alex@gmail.com", "")


def test_transient_failure_retries_and_eventually_succeeds(monkeypatch):
    notifier = ConsoleNotifier(max_attempts=3, base_delay=1)

    attempts = []
    delays = []

    def fake_delivery(recipient, message):
        attempts.append(1)

        if len(attempts) < 3:
            raise TransientNotificationError("temporary failure")

    monkeypatch.setattr(notifier, "_deliver_once", fake_delivery)
    monkeypatch.setattr("notifier.time.sleep", delays.append)

    notifier.deliver("alex@gmail.com", "Hello Alex")

    assert len(attempts) == 3
    assert delays == [1, 2]


def test_transient_failure_stops_after_max_attempts(monkeypatch):
    notifier = ConsoleNotifier(max_attempts=3, base_delay=1)

    attempts = []
    delays = []

    def fake_delivery(recipient, message):
        attempts.append(1)
        raise TransientNotificationError("temporary failure")

    monkeypatch.setattr(notifier, "_deliver_once", fake_delivery)
    monkeypatch.setattr("notifier.time.sleep", delays.append)

    with pytest.raises(TransientNotificationError, match="temporary failure"):
        notifier.deliver("alex@gmail.com", "Hello Alex")

    assert len(attempts) == 3
    assert delays == [1, 2]


def test_validation_errors_are_not_retried(monkeypatch):
    notifier = ConsoleNotifier()

    delivery_called = False

    def fake_delivery(recipient, message):
        nonlocal delivery_called
        delivery_called = True

    monkeypatch.setattr(notifier, "_deliver_once", fake_delivery)

    with pytest.raises(ValueError, match="Recipient cannot be empty"):
        notifier.deliver("", "Hello Alex")

    assert delivery_called is False


def test_retry_logging(monkeypatch, caplog):
    notifier = ConsoleNotifier(max_attempts=3, base_delay=1)

    attempts = []

    def fake_delivery(recipient, message):
        attempts.append(1)

        if len(attempts) == 1:
            raise TransientNotificationError("temporary failure")

    monkeypatch.setattr(notifier, "_deliver_once", fake_delivery)
    monkeypatch.setattr("notifier.time.sleep", lambda _: None)

    with caplog.at_level(logging.DEBUG, logger="notifier"):
        notifier.deliver("alex@gmail.com", "Hello Alex")

    assert "Notification delivery attempt=1/3" in caplog.text
    assert "Notification retry attempt=2/3 delay=1.00s" in caplog.text
    assert "Notification delivery succeeded on attempt=2" in caplog.text


def test_final_failure_is_logged(monkeypatch, caplog):
    notifier = ConsoleNotifier(max_attempts=2, base_delay=1)

    def fake_delivery(recipient, message):
        raise TransientNotificationError("temporary failure")

    monkeypatch.setattr(notifier, "_deliver_once", fake_delivery)
    monkeypatch.setattr("notifier.time.sleep", lambda _: None)

    with caplog.at_level(logging.ERROR, logger="notifier"):
        with pytest.raises(TransientNotificationError):
            notifier.deliver("alex@gmail.com", "Hello Alex")

    assert "Notification delivery failed after 2 attempts" in caplog.text


def test_configurable_retry_parameters(monkeypatch):
    notifier = ConsoleNotifier(max_attempts=2, base_delay=3)

    attempts = []
    delays = []

    def fake_delivery(recipient, message):
        attempts.append(1)
        raise TransientNotificationError("temporary failure")

    monkeypatch.setattr(notifier, "_deliver_once", fake_delivery)
    monkeypatch.setattr("notifier.time.sleep", delays.append)

    with pytest.raises(TransientNotificationError):
        notifier.deliver("alex@gmail.com", "Hello Alex")

    assert len(attempts) == 2
    assert delays == [3]


def test_jitter_is_applied(monkeypatch):
    notifier = ConsoleNotifier(
        max_attempts=2,
        base_delay=2,
        jitter=0.1,
    )

    delays = []

    def fake_delivery(recipient, message):
        raise TransientNotificationError("temporary failure")

    monkeypatch.setattr(notifier, "_deliver_once", fake_delivery)
    monkeypatch.setattr("notifier.time.sleep", delays.append)
    monkeypatch.setattr("notifier.random.uniform", lambda low, high: 0.1)

    with pytest.raises(TransientNotificationError):
        notifier.deliver("alex@gmail.com", "Hello Alex")

    # Attempt 1 delay = 2 * (2 ** 0) = 2
    # Jitter = +10%, so expected delay = 2.2
    assert delays == [2.2]

from unittest.mock import MagicMock, patch

from orchestrator.health_monitor import HealthMonitor, HealthStatus


def test_check_system_health_sets_ttl_on_health_keys():
    with patch("orchestrator.health_monitor.get_redis_client") as mock_get_redis_client:
        mock_redis = MagicMock()
        mock_get_redis_client.return_value = mock_redis

        monitor = HealthMonitor()

        with (
            patch.object(
                monitor,
                "_check_redis_health",
                return_value={"status": HealthStatus.HEALTHY},
            ),
            patch.object(
                monitor,
                "check_queue_health",
                return_value={"status": HealthStatus.HEALTHY},
            ),
        ):
            monitor.check_system_health()

        assert mock_redis.set.call_count == 2

        health_status_call = mock_redis.set.call_args_list[0]
        last_check_call = mock_redis.set.call_args_list[1]

        assert health_status_call.args[0] == monitor.health_status_key
        assert health_status_call.kwargs["ex"] == 300

        assert last_check_call.args[0] == monitor.last_check_key
        assert last_check_call.kwargs["ex"] == 300

from unittest.mock import MagicMock

import pytest

from orchestrator.load_balancer import BalancingStrategy, LoadBalancer


@pytest.fixture
def workers():
    return [
        {
            "worker_id": "worker-1",
            "active_tasks": 0,
            "capacity": 4,
        },
        {
            "worker_id": "worker-2",
            "active_tasks": 1,
            "capacity": 4,
        },
        {
            "worker_id": "worker-3",
            "active_tasks": 2,
            "capacity": 4,
        },
    ]


def make_load_balancer(strategy):
    load_balancer = LoadBalancer.__new__(LoadBalancer)
    load_balancer.worker_registry = MagicMock()
    load_balancer.strategy = strategy
    load_balancer.round_robin_index = 0
    load_balancer._wrr_current_weights = {}
    from threading import Lock

    load_balancer._wrr_lock = Lock()
    return load_balancer


def test_round_robin_selects_workers_in_order(workers):
    load_balancer = make_load_balancer(BalancingStrategy.ROUND_ROBIN)
    load_balancer._get_cached_workers = MagicMock(return_value=workers)

    selected = [load_balancer.select_worker()["worker_id"] for _ in range(4)]

    assert selected == [
        "worker-1",
        "worker-2",
        "worker-3",
        "worker-1",
    ]


def test_round_robin_returns_none_when_no_workers():
    load_balancer = make_load_balancer(BalancingStrategy.ROUND_ROBIN)
    load_balancer._get_cached_workers = MagicMock(return_value=[])

    assert load_balancer.select_worker() is None


def test_least_loaded_selects_worker_with_fewest_tasks(workers):
    load_balancer = make_load_balancer(BalancingStrategy.LEAST_LOADED)
    load_balancer.worker_registry.get_least_loaded_worker.return_value = workers[0]

    selected = load_balancer.select_worker()

    assert selected["worker_id"] == "worker-1"


def test_least_loaded_returns_none_when_no_workers():
    load_balancer = make_load_balancer(BalancingStrategy.LEAST_LOADED)
    load_balancer.worker_registry.get_least_loaded_worker.return_value = None

    assert load_balancer.select_worker() is None


def test_queue_based_returns_worker_when_available(workers):
    load_balancer = make_load_balancer(BalancingStrategy.QUEUE_BASED)
    load_balancer.worker_registry.get_least_loaded_worker.return_value = workers[1]

    selected = load_balancer.select_worker()

    assert selected["worker_id"] == "worker-2"


def test_queue_based_returns_none_when_no_workers():
    load_balancer = make_load_balancer(BalancingStrategy.QUEUE_BASED)
    load_balancer.worker_registry.get_least_loaded_worker.return_value = None

    assert load_balancer.select_worker() is None


def test_weighted_least_loaded_uses_relative_load():
    workers = [
        {
            "worker_id": "worker-1",
            "active_tasks": 3,
            "capacity": 4,
            "weight": 4,
        },
        {
            "worker_id": "worker-2",
            "active_tasks": 2,
            "capacity": 4,
            "weight": 1,
        },
    ]

    load_balancer = make_load_balancer(BalancingStrategy.WEIGHTED_LEAST_LOADED)
    load_balancer.worker_registry.get_available_workers.return_value = workers

    selected = load_balancer.select_worker()

    assert selected["worker_id"] == "worker-1"


def test_weighted_round_robin_returns_none_without_workers():
    load_balancer = make_load_balancer(BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    load_balancer.worker_registry.get_available_workers.return_value = []

    assert load_balancer.select_worker() is None


def test_weighted_round_robin_distributes_by_weight():
    workers = [
        {
            "worker_id": "worker-1",
            "active_tasks": 0,
            "capacity": 4,
            "weight": 2,
        },
        {
            "worker_id": "worker-2",
            "active_tasks": 0,
            "capacity": 4,
            "weight": 1,
        },
    ]

    load_balancer = make_load_balancer(BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    load_balancer.worker_registry.get_available_workers.return_value = workers

    selected = [load_balancer.select_worker()["worker_id"] for _ in range(3)]

    assert selected.count("worker-1") == 2
    assert selected.count("worker-2") == 1


def test_switch_strategy():
    load_balancer = make_load_balancer(BalancingStrategy.ROUND_ROBIN)

    load_balancer.switch_strategy(BalancingStrategy.LEAST_LOADED)

    assert load_balancer.strategy == BalancingStrategy.LEAST_LOADED

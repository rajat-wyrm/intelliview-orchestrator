"""
Unit tests for the LoadBalancer selection strategies.
"""

from collections import Counter

from orchestrator.load_balancer import BalancingStrategy, LoadBalancer


class FakeRegistry:
    def __init__(self, workers):
        self._workers = workers

    def get_available_workers(self):
        return [w for w in self._workers if w["status"] == "healthy" and w["active_tasks"] < w["capacity"]]

    def get_least_loaded_worker(self):
        available = self.get_available_workers()
        return min(available, key=lambda w: w["active_tasks"]) if available else None

    def get_worker_statistics(self):
        return {
            "total_workers": len(self._workers),
            "total_capacity": sum(w["capacity"] for w in self._workers),
            "total_active_tasks": sum(w["active_tasks"] for w in self._workers),
            "capacity_utilization": 0,
        }


def _make_workers():
    return [
        {
            "worker_id": "w1",
            "capacity": 4,
            "active_tasks": 3,
            "status": "healthy",
            "weight": 1,
        },
        {
            "worker_id": "w2",
            "capacity": 4,
            "active_tasks": 1,
            "status": "healthy",
            "weight": 1,
        },
        {
            "worker_id": "w3",
            "capacity": 4,
            "active_tasks": 2,
            "status": "healthy",
            "weight": 1,
        },
    ]


# ===========================================================================
# Existing tests (unchanged)
# ===========================================================================


def test_least_loaded_picks_minimum():
    lb = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
    lb.worker_registry = FakeRegistry(_make_workers())
    assert lb.select_worker()["worker_id"] == "w2"


def test_round_robin_rotates():
    lb = LoadBalancer(strategy=BalancingStrategy.ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(_make_workers())
    first = lb.select_worker()["worker_id"]
    second = lb.select_worker()["worker_id"]
    third = lb.select_worker()["worker_id"]
    assert len({first, second, third}) == 3


def test_no_workers_returns_none():
    lb = LoadBalancer()
    lb.worker_registry = FakeRegistry([])
    assert lb.select_worker() is None


def test_unhealthy_workers_excluded():
    workers = _make_workers()
    workers[0]["status"] = "unhealthy"
    lb = LoadBalancer()
    lb.worker_registry = FakeRegistry(workers)
    assert lb.select_worker()["worker_id"] in {"w2", "w3"}


def test_full_capacity_workers_excluded():
    workers = _make_workers()
    workers[1]["active_tasks"] = 4  # w2 at capacity
    lb = LoadBalancer()
    lb.worker_registry = FakeRegistry(workers)
    assert lb.select_worker()["worker_id"] in {"w3"}


# ===========================================================================
# NEW: Weighted Round Robin (SWRR) tests
# ===========================================================================


def _make_weighted_workers():
    """Workers with weights 5, 1, 1 — A should get 5/7 of tasks."""
    return [
        {"worker_id": "A", "capacity": 10, "weight": 5, "active_tasks": 0, "status": "healthy"},
        {"worker_id": "B", "capacity": 10, "weight": 1, "active_tasks": 0, "status": "healthy"},
        {"worker_id": "C", "capacity": 10, "weight": 1, "active_tasks": 0, "status": "healthy"},
    ]


def test_wrr_proportional_distribution():
    """Over 7 calls with weights {A:5, B:1, C:1}, A gets 5, B gets 1, C gets 1."""
    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(_make_weighted_workers())

    selections = [lb.select_worker()["worker_id"] for _ in range(7)]
    counts = Counter(selections)

    assert counts["A"] == 5
    assert counts["B"] == 1
    assert counts["C"] == 1


def test_wrr_smooth_interleaving():
    """The distribution should be smooth — not all A first, then B, then C.

    With Nginx SWRR and weights {A:5, B:1, C:1}, the sequence is:
    A, A, B, A, C, A, A  (B and C are interleaved among A's).
    """
    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(_make_weighted_workers())

    selections = [lb.select_worker()["worker_id"] for _ in range(7)]

    # The first 5 should NOT all be "A" — that would be non-smooth
    first_five = selections[:5]
    assert set(first_five) != {"A"}, f"Not smooth: {selections}"


def test_wrr_equal_weights_round_robins():
    """Equal weights should distribute evenly like plain round robin."""
    workers = [
        {"worker_id": "X", "capacity": 4, "weight": 1, "active_tasks": 0, "status": "healthy"},
        {"worker_id": "Y", "capacity": 4, "weight": 1, "active_tasks": 0, "status": "healthy"},
        {"worker_id": "Z", "capacity": 4, "weight": 1, "active_tasks": 0, "status": "healthy"},
    ]
    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(workers)

    selections = [lb.select_worker()["worker_id"] for _ in range(9)]
    counts = Counter(selections)

    assert counts["X"] == 3
    assert counts["Y"] == 3
    assert counts["Z"] == 3


def test_wrr_single_worker():
    """Single worker should always be selected."""
    workers = [
        {"worker_id": "solo", "capacity": 4, "weight": 5, "active_tasks": 0, "status": "healthy"},
    ]
    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(workers)

    for _ in range(10):
        assert lb.select_worker()["worker_id"] == "solo"


def test_wrr_no_workers_returns_none():
    """No available workers should return None."""
    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry([])
    assert lb.select_worker() is None


def test_wrr_excludes_unhealthy():
    """Unhealthy workers should be excluded from SWRR selection."""
    workers = _make_weighted_workers()
    workers[0]["status"] = "unhealthy"  # A is down

    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(workers)

    selections = [lb.select_worker()["worker_id"] for _ in range(4)]
    assert "A" not in selections
    counts = Counter(selections)
    assert counts["B"] == 2
    assert counts["C"] == 2


def test_wrr_excludes_at_capacity():
    """Workers at full capacity should be excluded from SWRR selection."""
    workers = _make_weighted_workers()
    workers[0]["active_tasks"] = 10  # A at capacity (capacity=10)

    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(workers)

    selections = [lb.select_worker()["worker_id"] for _ in range(4)]
    assert "A" not in selections


def test_wrr_respects_weight_field():
    """Weight field should be used, not capacity, for SWRR.

    Worker X has capacity=10 but weight=1.
    Worker Y has capacity=2 but weight=3.
    Over 4 calls: Y should get 3, X should get 1.
    """
    workers = [
        {"worker_id": "X", "capacity": 10, "weight": 1, "active_tasks": 0, "status": "healthy"},
        {"worker_id": "Y", "capacity": 10, "weight": 3, "active_tasks": 0, "status": "healthy"},
    ]
    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(workers)

    selections = [lb.select_worker()["worker_id"] for _ in range(4)]
    counts = Counter(selections)

    assert counts["Y"] == 3
    assert counts["X"] == 1

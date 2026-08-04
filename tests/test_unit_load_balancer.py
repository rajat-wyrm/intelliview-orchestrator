"""
Unit tests for the LoadBalancer selection strategies.
"""

from orchestrator.load_balancer import BalancingStrategy, LoadBalancer


class FakeRegistry:
    def __init__(self, workers):
        self._workers = workers

    def get_available_workers(self, required_tag=None):
        available = [
            w for w in self._workers if w["status"] == "healthy" and w["active_tasks"] < w["capacity"]
        ]
        if required_tag is not None:
            available = [w for w in available if required_tag in w.get("tags", [])]
        return available

    def get_least_loaded_worker(self, required_tag=None):
        available = self.get_available_workers(required_tag=required_tag)
        return min(available, key=lambda w: w["active_tasks"]) if available else None

    def get_worker(self, worker_id):
        for w in self._workers:
            if w["worker_id"] == worker_id:
                return w
        return None

    def get_worker_statistics(self):
        return {
            "total_workers": len(self._workers),
            "total_capacity": sum(w["capacity"] for w in self._workers),
            "total_active_tasks": sum(w["active_tasks"] for w in self._workers),
            "capacity_utilization": 0,
        }


def _make_workers():
    return [
        {"worker_id": "w1", "capacity": 4, "active_tasks": 3, "status": "healthy", "tags": []},
        {"worker_id": "w2", "capacity": 4, "active_tasks": 1, "status": "healthy", "tags": []},
        {"worker_id": "w3", "capacity": 4, "active_tasks": 2, "status": "healthy", "tags": []},
    ]


def _make_tagged_workers():
    """Workers with mixed capability tags, for tag-routing tests."""
    return [
        {"worker_id": "w1", "capacity": 4, "active_tasks": 1, "status": "healthy", "tags": ["gpu", "video"]},
        {"worker_id": "w2", "capacity": 4, "active_tasks": 0, "status": "healthy", "tags": ["audio"]},
        {"worker_id": "w3", "capacity": 4, "active_tasks": 2, "status": "healthy", "tags": []},
    ]


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
def test_weighted_least_loaded_prefers_higher_weight_worker():
    workers = [
        {
            "worker_id": "w1",
            "capacity": 10,
            "active_tasks": 4,
            "status": "healthy",
            "weight": 1,
        },
        {
            "worker_id": "w2",
            "capacity": 10,
            "active_tasks": 6,
            "status": "healthy",
            "weight": 3,
        },
    ]


def test_weighted_least_loaded_prefers_higher_weight_worker():
    workers = [
        {
            "worker_id": "w1",
            "capacity": 10,
            "active_tasks": 4,
            "status": "healthy",
            "weight": 1,
        },
        {
            "worker_id": "w2",
            "capacity": 10,
            "active_tasks": 6,
            "status": "healthy",
            "weight": 3,
        },
    ]

    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_LEAST_LOADED)
    lb.worker_registry = FakeRegistry(workers)

    selected = lb.select_worker()

    assert selected["worker_id"] == "w2"


def test_weighted_least_loaded_prefers_higher_weight():
    workers = [
        {
            "worker_id": "w1",
            "capacity": 4,
            "active_tasks": 2,
            "status": "healthy",
            "weight": 1,
        },
        {
            "worker_id": "w2",
            "capacity": 4,
            "active_tasks": 2,
            "status": "healthy",
            "weight": 2,
        },
    ]

    lb = LoadBalancer(strategy=BalancingStrategy.WEIGHTED_LEAST_LOADED)

    lb.worker_registry = FakeRegistry(workers)

    selected = lb.select_worker()

    assert selected["worker_id"] == "w2"
=======
    counts = Counter(results)
    assert len(results) == 90
    assert lb.round_robin_index == 90
    for worker in workers:
        assert counts[worker["worker_id"]] == 30


# ========== Capability tag routing tests (Issue #2) ==========


def test_required_tag_routes_to_matching_worker():
    """A task requiring a specific tag only ever goes to a worker that has it."""
    lb = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
    lb.worker_registry = FakeRegistry(_make_tagged_workers())

    worker = lb.select_worker(required_tag="gpu")
    assert worker is not None
    assert worker["worker_id"] == "w1"
    assert "gpu" in worker["tags"]


def test_required_tag_never_routes_to_non_matching_worker():
    """Even if a non-matching worker is less loaded, it must never be picked."""
    workers = _make_tagged_workers()
    # w2 (audio only) is the least loaded overall, but doesn't have "gpu".
    lb = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
    lb.worker_registry = FakeRegistry(workers)

    worker = lb.select_worker(required_tag="gpu")
    assert worker["worker_id"] != "w2"
    assert worker["worker_id"] == "w1"


def test_required_tag_no_match_returns_none():
    """If no worker has the required tag, no worker should be silently substituted."""
    lb = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
    lb.worker_registry = FakeRegistry(_make_tagged_workers())

    assert lb.select_worker(required_tag="nonexistent-tag") is None


def test_no_tag_specified_falls_back_to_all_workers():
    """When no tag is requested, all healthy/available workers remain eligible."""
    lb = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
    lb.worker_registry = FakeRegistry(_make_tagged_workers())

    worker = lb.select_worker(required_tag=None)
    # w2 has no tags but is least loaded (0 active tasks) and must still be eligible.
    assert worker["worker_id"] == "w2"


def test_required_tag_respected_under_round_robin():
    """Round robin selection must also honor required_tag filtering."""
    workers = _make_tagged_workers()
    lb = LoadBalancer(strategy=BalancingStrategy.ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(workers)

    for _ in range(5):
        worker = lb.select_worker(required_tag="video")
        assert worker["worker_id"] == "w1"  # only w1 has "video"
>>>>>>> pr-645-head

"""
Unit tests for the LoadBalancer selection strategies.
"""

import threading
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
        {"worker_id": "w1", "capacity": 4, "active_tasks": 3, "status": "healthy"},
        {"worker_id": "w2", "capacity": 4, "active_tasks": 1, "status": "healthy"},
        {"worker_id": "w3", "capacity": 4, "active_tasks": 2, "status": "healthy"},
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


def test_round_robin_thread_safety():
    """
    Simulates many concurrent calls to select_worker() under ROUND_ROBIN
    strategy and confirms tasks are distributed evenly with no lost or
    duplicate increments, proving the round_robin_index update is atomic.
    """
    workers = _make_workers()
    lb = LoadBalancer(strategy=BalancingStrategy.ROUND_ROBIN)
    lb.worker_registry = FakeRegistry(workers)

    results = []
    results_lock = threading.Lock()

    def call_select_worker():
        worker = lb.select_worker()
        with results_lock:
            results.append(worker["worker_id"])

    threads = [threading.Thread(target=call_select_worker) for _ in range(90)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    counts = Counter(results)
    assert len(results) == 90
    assert lb.round_robin_index == 90
    for worker in workers:
        assert counts[worker["worker_id"]] == 30

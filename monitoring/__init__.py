"""
Monitoring Module

Provides real-time dashboards and observability for the AI Interview Orchestration system.
"""

from monitoring.dashboard_api import create_dashboard_routes
from monitoring.metrics_collector import MetricsCollector
from monitoring.websocket_manager import WebSocketManager, ws_manager

__all__ = [
    "MetricsCollector",
    "WebSocketManager",
    "create_dashboard_routes",
    "ws_manager",
]

try:
    from monitoring.prometheus_metrics import get_metrics_text  # noqa: F401

    __all__.append("get_metrics_text")
except ImportError:
    pass

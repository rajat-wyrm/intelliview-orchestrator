from prometheus_client import start_http_server
from monitoring.prometheus_metrics import registry


def start_worker_metrics():
    print("Starting worker metrics server on port 9101")
    start_http_server(
        port=9101,
        registry=registry
    )
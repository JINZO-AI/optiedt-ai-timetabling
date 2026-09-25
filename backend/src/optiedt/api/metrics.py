"""Prometheus metrics exposed at /metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "optiedt_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "optiedt_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
SOLVER_RUNS = Gauge("optiedt_solver_runs", "Solver runs by status", ["status"])
WORKERS_ALIVE = Gauge("optiedt_workers_alive", "Workers with a heartbeat in the last minute")
QUEUE_OLDEST = Gauge(
    "optiedt_queue_oldest_seconds", "Age of the oldest queued solver run (0 when none waits)"
)


def observe_request(method: str, route: str, status: int, seconds: float) -> None:
    HTTP_REQUESTS.labels(method, route, str(status)).inc()
    HTTP_LATENCY.labels(method, route).observe(seconds)

#!/usr/bin/env python3
"""Minimal Prometheus exporter for LiteLLM health and route inventory."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


LITELLM_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
LITELLM_API_KEY = os.environ.get("LITELLM_EXPORTER_API_KEY", "").strip()
LISTEN_HOST = os.environ.get("LITELLM_EXPORTER_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("LITELLM_EXPORTER_PORT", "11436"))
SCRAPE_TIMEOUT = float(os.environ.get("LITELLM_EXPORTER_TIMEOUT", "5"))


def fetch(path: str) -> tuple[int, bytes]:
    headers = {}
    if LITELLM_API_KEY:
        headers["x-litellm-api-key"] = LITELLM_API_KEY
    request = urllib.request.Request(f"{LITELLM_BASE_URL}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=SCRAPE_TIMEOUT) as response:
        return response.status, response.read()


def metric_line(name: str, value: float | int) -> str:
    return f"{name} {value}"


def collect_metrics() -> str:
    lines = [
        "# HELP litellm_up Whether LiteLLM is reachable and healthy.",
        "# TYPE litellm_up gauge",
        "# HELP litellm_model_routes Number of model routes exposed by LiteLLM.",
        "# TYPE litellm_model_routes gauge",
        "# HELP litellm_health_scrape_duration_seconds Time spent scraping LiteLLM state.",
        "# TYPE litellm_health_scrape_duration_seconds gauge",
    ]

    started = time.monotonic()
    try:
        status, _payload = fetch("/health/liveness")
        litellm_up = 1 if status == 200 else 0
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        lines.append(metric_line("litellm_up", 0))
        lines.append(metric_line("litellm_model_routes", 0))
        lines.append(metric_line("litellm_health_scrape_duration_seconds", time.monotonic() - started))
        return "\n".join(lines) + "\n"

    route_count = 0
    try:
        model_status, model_payload = fetch("/models")
        if model_status == 200:
            data = json.loads(model_payload.decode("utf-8"))
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                route_count = len(data["data"])
            elif isinstance(data, list):
                route_count = len(data)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        route_count = 0

    lines.append(metric_line("litellm_up", litellm_up))
    lines.append(metric_line("litellm_model_routes", route_count))

    lines.append(metric_line("litellm_health_scrape_duration_seconds", time.monotonic() - started))
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok\n")
            return

        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        payload = collect_metrics().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    server = HTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

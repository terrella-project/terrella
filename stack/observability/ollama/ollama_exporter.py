#!/usr/bin/env python3
"""Minimal Prometheus exporter for a host Ollama instance.

Exposes:
  - ollama_up
  - ollama_loaded_models
  - ollama_installed_models
  - ollama_model_loaded{model,...}
  - ollama_model_size_bytes{model,...}
  - ollama_model_vram_bytes{model,...}
  - ollama_model_installed_bytes{model,...}
  - ollama_model_expires_unixtime{model,...}
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
LISTEN_HOST = os.environ.get("OLLAMA_EXPORTER_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("OLLAMA_EXPORTER_PORT", "11435"))
SCRAPE_TIMEOUT = float(os.environ.get("OLLAMA_EXPORTER_TIMEOUT", "5"))


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(f"{OLLAMA_BASE_URL}{path}")
    with urllib.request.urlopen(req, timeout=SCRAPE_TIMEOUT) as response:
        return json.load(response)


def prom_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def metric_line(name: str, value: float | int, labels: dict[str, str] | None = None) -> str:
    if labels:
        rendered = ",".join(f'{key}="{prom_escape(val)}"' for key, val in sorted(labels.items()))
        return f"{name}{{{rendered}}} {value}"
    return f"{name} {value}"


def iso_to_unix(ts: str | None) -> float:
    if not ts:
        return 0
    normalized = ts.replace("Z", "+00:00")
    try:
        return __import__("datetime").datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return 0


def collect_metrics() -> str:
    lines = [
        "# HELP ollama_up Whether Ollama is reachable.",
        "# TYPE ollama_up gauge",
        "# HELP ollama_loaded_models Number of models currently loaded in Ollama.",
        "# TYPE ollama_loaded_models gauge",
        "# HELP ollama_installed_models Number of models installed in Ollama.",
        "# TYPE ollama_installed_models gauge",
        "# HELP ollama_model_loaded Whether a model is currently loaded in Ollama.",
        "# TYPE ollama_model_loaded gauge",
        "# HELP ollama_model_size_bytes Model size in bytes.",
        "# TYPE ollama_model_size_bytes gauge",
        "# HELP ollama_model_installed_bytes Installed model size in bytes.",
        "# TYPE ollama_model_installed_bytes gauge",
        "# HELP ollama_model_vram_bytes VRAM currently used by a loaded model in bytes.",
        "# TYPE ollama_model_vram_bytes gauge",
        "# HELP ollama_model_expires_unixtime When the loaded model is scheduled to expire from memory.",
        "# TYPE ollama_model_expires_unixtime gauge",
    ]

    try:
        tags = fetch_json("/api/tags").get("models", [])
        ps = fetch_json("/api/ps").get("models", [])
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        lines.append(metric_line("ollama_up", 0))
        lines.append(metric_line("ollama_loaded_models", 0))
        lines.append(metric_line("ollama_installed_models", 0))
        return "\n".join(lines) + "\n"

    installed = {}
    for model in tags:
        name = model.get("name")
        if not name:
            continue
        details = model.get("details", {})
        installed[name] = {
            "name": name,
            "family": details.get("family", ""),
            "quantization": details.get("quantization_level", ""),
            "parameter_size": details.get("parameter_size", ""),
            "context_length": str(model.get("context_length") or ""),
            "size": int(model.get("size") or 0),
            "size_vram": 0,
            "expires_at": "",
            "loaded": 0,
        }

    for model in ps:
        name = model.get("name")
        if not name:
            continue
        details = model.get("details", {})
        current = installed.get(
            name,
            {
                "name": name,
                "family": details.get("family", ""),
                "quantization": details.get("quantization_level", ""),
                "parameter_size": details.get("parameter_size", ""),
                "context_length": str(model.get("context_length") or ""),
                "size": int(model.get("size") or 0),
                "size_vram": 0,
                "expires_at": "",
                "loaded": 0,
            },
        )
        current.update(
            {
                "family": current.get("family") or details.get("family", ""),
                "quantization": current.get("quantization") or details.get("quantization_level", ""),
                "parameter_size": current.get("parameter_size") or details.get("parameter_size", ""),
                "context_length": current.get("context_length") or str(model.get("context_length") or ""),
                "size": int(current.get("size") or model.get("size") or 0),
                "size_vram": int(model.get("size_vram") or 0),
                "expires_at": model.get("expires_at") or "",
                "loaded": 1,
            }
        )
        installed[name] = current

    lines.append(metric_line("ollama_up", 1))
    lines.append(metric_line("ollama_loaded_models", sum(m["loaded"] for m in installed.values())))
    lines.append(metric_line("ollama_installed_models", len(installed)))

    for model in sorted(installed.values(), key=lambda item: item["name"]):
        labels = {
            "model": model["name"],
            "family": model["family"],
            "quantization": model["quantization"],
            "parameter_size": model["parameter_size"],
            "context_length": model["context_length"],
        }
        lines.append(metric_line("ollama_model_loaded", model["loaded"], labels))
        lines.append(metric_line("ollama_model_size_bytes", model["size"], labels))
        lines.append(metric_line("ollama_model_installed_bytes", model["size"], labels))
        lines.append(metric_line("ollama_model_vram_bytes", model["size_vram"], labels))
        lines.append(metric_line("ollama_model_expires_unixtime", iso_to_unix(model["expires_at"]), labels))

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

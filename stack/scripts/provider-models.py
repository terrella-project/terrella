#!/usr/bin/env python3
"""Fetch provider model IDs used by LiteLLM config tooling.

This helper keeps provider-specific filtering rules in one place so
`list-models.sh` and `update-litellm-config.sh` stay consistent.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


OPENAI_CORE_MODELS = {
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5.1",
    "gpt-5.2",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.5",
    "o1",
    "o1-pro",
    "o3",
    "o3-mini",
    "o4-mini",
}


def fail(message: str, code: int = 1) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def fetch_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        detail = f"{exc.code} {exc.reason}"
        if body:
            detail = f"{detail}: {body}"
        fail(f"{url} returned {detail}")
    except urllib.error.URLError as exc:
        fail(f"failed to reach {url}: {exc.reason}")


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        fail(f"{name} is not set")
    return value


def anthropic_models() -> list[str]:
    api_key = require_env("ANTHROPIC_API_KEY")
    payload = fetch_json(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    return sorted({item["id"] for item in payload.get("data", []) if item.get("id")})


def gemini_models() -> list[str]:
    api_key = require_env("GEMINI_API_KEY")
    payload = fetch_json(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    )
    model_ids = set()
    for item in payload.get("models", []):
        name = item.get("name", "").replace("models/", "")
        if "gemini" in name.lower():
            model_ids.add(name)
    return sorted(model_ids)


def openai_models() -> list[str]:
    api_key = require_env("OPENAI_API_KEY")
    payload = fetch_json(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    model_ids = set()
    for item in payload.get("data", []):
        model_id = item.get("id", "")
        if model_id in OPENAI_CORE_MODELS:
            model_ids.add(model_id)
    return sorted(model_ids)


def ollama_models() -> list[str]:
    payload = fetch_json("http://localhost:11434/api/tags")
    return sorted(
        {item["name"] for item in payload.get("models", []) if item.get("name")}
    )


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: provider-models.py [anthropic|gemini|openai|ollama]")
        return 0 if len(sys.argv) == 2 else 1

    provider = sys.argv[1]
    if provider == "anthropic":
        models = anthropic_models()
    elif provider == "gemini":
        models = gemini_models()
    elif provider == "openai":
        models = openai_models()
    elif provider == "ollama":
        models = ollama_models()
    else:
        fail(f"unknown provider: {provider}")

    for model_id in models:
        print(model_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

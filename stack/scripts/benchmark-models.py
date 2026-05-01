#!/usr/bin/env python3
"""
benchmark-models.py — Benchmark LiteLLM-proxied models on local hardware.

Metrics per model (across all prompts × --runs iterations):
    TTFT      time to first token (ms), measured via streaming
    Tok/s     output token generation throughput
    p50/p95   total request latency percentiles

Defaults to ollama (local) models only; pass --all for cloud providers too.
Historical baseline from LiteLLM_SpendLogs is shown when Postgres is reachable.

Usage (from the stack/ directory):
    python3 scripts/benchmark-models.py [options]

Options:
    --key KEY         Virtual key (or set LITELLM_KEY env var)
    --host URL        LiteLLM proxy URL  [default: http://localhost:4000]
    --models m1,m2    Explicit comma-separated model names to benchmark
    --all             Include cloud models (Anthropic / Gemini / OpenAI)
    --runs N          Iterations per prompt per model  [default: 3]
    --timeout S       Per-request timeout in seconds   [default: 120]
    --no-vram         Skip nvidia-smi VRAM readings
    --no-history      Skip Postgres historical comparison
    --db-url URL      Postgres URL (or set DATABASE_URL)
"""

from __future__ import annotations

import argparse
import http.client
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Benchmark prompts
# ---------------------------------------------------------------------------

PROMPTS = [
    {
        "name": "short",
        "messages": [{"role": "user", "content": "Reply with exactly three words: benchmark test successful."}],
        "max_tokens": 20,
    },
    {
        "name": "code",
        "messages": [{"role": "user", "content": "Write a Python function to compute fibonacci(n) iteratively."}],
        "max_tokens": 150,
    },
    {
        "name": "explain",
        "messages": [{"role": "user", "content": "In two sentences, explain the difference between TCP and UDP."}],
        "max_tokens": 100,
    },
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Sample:
    ttft_ms: float
    total_ms: float
    output_tokens: int
    tok_per_sec: float


@dataclass
class ModelResult:
    model: str
    provider: str
    samples: list[Sample] = field(default_factory=list)
    vram_mb: int | None = None
    error: str | None = None

    def _sorted(self, key: str) -> list[float]:
        return sorted(getattr(s, key) for s in self.samples)

    def p50(self, key: str) -> float | None:
        vals = self._sorted(key)
        return vals[len(vals) // 2] if vals else None

    def p95(self, key: str) -> float | None:
        vals = self._sorted(key)
        if not vals:
            return None
        return vals[max(0, math.ceil(len(vals) * 0.95) - 1)]

    def median_tok_per_sec(self) -> float | None:
        return self.p50("tok_per_sec")


@dataclass
class HistoricalData:
    calls: int
    p50_ms: float
    p95_ms: float
    avg_tok_per_sec: float | None


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# Model discovery from config.yaml (no external deps)
# ---------------------------------------------------------------------------

def parse_config_models(config_path: Path) -> list[tuple[str, str]]:
    """
    Return [(model_name, provider)] parsed from config.yaml.

    Deduplicates on underlying model ID (first occurrence wins) so that
    manual aliases like 'deepseek' are preferred over raw catalog entries
    like 'ollama/deepseek-r1:14b' that map to the same model.
    """
    if not config_path.exists():
        return []

    text = config_path.read_text()

    # Two-pass: collect (model_name, underlying_model) pairs.
    pairs: list[tuple[str, str]] = []
    current_name: str | None = None
    current_model: str | None = None

    for line in text.splitlines():
        m = re.match(r"^\s*-\s+model_name:\s+(.+)$", line)
        if m:
            if current_name and current_model:
                pairs.append((current_name, current_model))
            current_name = m.group(1).strip().strip('"').strip("'")
            current_model = None
            continue

        # First 'model:' under litellm_params (before the next model_name entry)
        m = re.match(r"^\s+model:\s+(.+)$", line)
        if m and current_name is not None and current_model is None:
            current_model = m.group(1).strip().strip('"').strip("'")

    if current_name and current_model:
        pairs.append((current_name, current_model))

    # Deduplicate on underlying model, keeping first occurrence.
    seen_underlying: set[str] = set()
    seen_name: set[str] = set()
    results: list[tuple[str, str]] = []
    for name, underlying in pairs:
        if name in seen_name or underlying in seen_underlying:
            continue
        seen_name.add(name)
        seen_underlying.add(underlying)
        results.append((name, _infer_provider(underlying)))

    return results


def _infer_provider(underlying: str) -> str:
    if underlying.startswith("ollama/"):
        return "ollama"
    if underlying.startswith("anthropic/") or re.match(r"claude-", underlying):
        return "anthropic"
    if underlying.startswith("gemini/"):
        return "gemini"
    if underlying.startswith("openai/") or re.match(r"(gpt|o[134])", underlying):
        return "openai"
    return "unknown"


def select_models(args: argparse.Namespace, config_models: list[tuple[str, str]]) -> list[tuple[str, str]]:
    if args.models:
        config_map = dict(config_models)
        return [(m.strip(), config_map.get(m.strip(), "unknown")) for m in args.models.split(",")]
    if args.all:
        return config_models
    # Default: local chat models only. Skip raw catalog entries (model_name contains '/')
    # and embedding models (not compatible with /v1/chat/completions).
    return [
        (name, prov) for name, prov in config_models
        if prov == "ollama"
        and "/" not in name
        and not re.search(r"embed", name, re.IGNORECASE)
    ]


# ---------------------------------------------------------------------------
# VRAM via nvidia-smi
# ---------------------------------------------------------------------------

def read_vram_mb() -> int | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip().split("\n")[0])
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


# ---------------------------------------------------------------------------
# Streaming inference (stdlib only)
# ---------------------------------------------------------------------------

def stream_call(
    host: str,
    key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    timeout: int,
) -> Sample:
    parsed = urllib.parse.urlparse(host)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "Content-Length": str(len(body)),
    }

    if parsed.scheme == "https":
        import ssl
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            parsed.hostname, port, timeout=timeout,
            context=ssl.create_default_context(),
        )
    else:
        conn = http.client.HTTPConnection(parsed.hostname, port, timeout=timeout)

    t_start = time.monotonic()
    t_first_token: float | None = None
    output_tokens = 0
    output_chars = 0

    try:
        conn.request("POST", "/v1/chat/completions", body=body, headers=headers)
        resp = conn.getresponse()

        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}: {resp.read(512).decode(errors='replace')}")

        buf = b""
        done = False
        while not done:
            chunk = resp.read(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line.startswith(b"data: "):
                    continue
                payload = line[6:]
                if payload == b"[DONE]":
                    done = True
                    break
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices") or []
                if choices:
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content") or ""
                    if content:
                        if t_first_token is None:
                            t_first_token = time.monotonic()
                        output_chars += len(content)

                usage = data.get("usage") or {}
                if usage.get("completion_tokens"):
                    output_tokens = int(usage["completion_tokens"])

    finally:
        conn.close()

    t_end = time.monotonic()
    if t_first_token is None:
        t_first_token = t_end

    if output_tokens == 0 and output_chars > 0:
        output_tokens = max(1, output_chars // 4)

    ttft_ms = (t_first_token - t_start) * 1000
    total_ms = (t_end - t_start) * 1000
    gen_secs = t_end - t_first_token
    tok_per_sec = output_tokens / gen_secs if gen_secs > 0.001 and output_tokens > 0 else 0.0

    return Sample(ttft_ms=ttft_ms, total_ms=total_ms, output_tokens=output_tokens, tok_per_sec=tok_per_sec)


# ---------------------------------------------------------------------------
# Postgres historical baseline
# ---------------------------------------------------------------------------

_HISTORY_SQL = """
SELECT
    model,
    COUNT(*) AS calls,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM ("endTime" - "startTime")) * 1000
    ) AS p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM ("endTime" - "startTime")) * 1000
    ) AS p95_ms,
    AVG(
        CASE WHEN "endTime" > "startTime" AND completion_tokens > 0
             THEN completion_tokens::float / NULLIF(EXTRACT(EPOCH FROM ("endTime" - "startTime")), 0)
             ELSE NULL END
    ) AS avg_tok_per_sec
FROM "LiteLLM_SpendLogs"
WHERE "startTime" > NOW() - INTERVAL '30 days'
GROUP BY model
HAVING COUNT(*) >= 3
ORDER BY avg_tok_per_sec DESC NULLS LAST
"""


def write_results(db_url: str, results: list[ModelResult]) -> None:
    """Persist benchmark results to Postgres for historical tracking."""
    try:
        import psycopg2  # type: ignore[import]
    except ImportError:
        print("Note: psycopg2 not installed — skipping result persistence.", file=sys.stderr)
        return

    from datetime import datetime, timezone
    run_at = datetime.now(timezone.utc)

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        for r in results:
            cur.execute(
                """
                INSERT INTO benchmark_results
                    (run_at, model, provider, ttft_p50_ms, tok_per_sec_p50,
                     lat_p50_ms, lat_p95_ms, vram_mb, sample_count, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run_at,
                    r.model,
                    r.provider,
                    r.p50("ttft_ms"),
                    r.median_tok_per_sec(),
                    r.p50("total_ms"),
                    r.p95("total_ms"),
                    r.vram_mb,
                    len(r.samples),
                    r.error,
                ),
            )
        conn.commit()
        cur.close()
        conn.close()
        print(f"Results saved to Postgres ({len(results)} model(s)).")
    except Exception as exc:
        print(f"Note: could not write benchmark results to Postgres: {exc}", file=sys.stderr)


def query_history(db_url: str) -> dict[str, HistoricalData]:
    try:
        import psycopg2  # type: ignore[import]
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(_HISTORY_SQL)
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception:
        return {}

    result: dict[str, HistoricalData] = {}
    for model, calls, p50, p95, avg_tok in rows:
        result[str(model)] = HistoricalData(
            calls=int(calls),
            p50_ms=float(p50) if p50 is not None else 0.0,
            p95_ms=float(p95) if p95 is not None else 0.0,
            avg_tok_per_sec=float(avg_tok) if avg_tok is not None else None,
        )
    return result


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_model(
    host: str,
    key: str,
    model: str,
    provider: str,
    runs: int,
    timeout: int,
    track_vram: bool,
) -> ModelResult:
    result = ModelResult(model=model, provider=provider)
    print(f"  {model}", end="", flush=True)

    vram_before = read_vram_mb() if track_vram else None

    for prompt in PROMPTS:
        for _ in range(runs):
            try:
                sample = stream_call(host, key, model, prompt["messages"], prompt["max_tokens"], timeout)
                result.samples.append(sample)
                print(".", end="", flush=True)
            except Exception as exc:
                result.error = str(exc)
                print(f" ERROR: {exc}")
                return result

    if track_vram:
        vram_after = read_vram_mb()
        # Report VRAM in use after inference (model is loaded); delta shows footprint.
        if vram_after is not None and vram_before is not None:
            result.vram_mb = vram_after - vram_before if vram_after > vram_before else vram_after

    print()
    return result


# ---------------------------------------------------------------------------
# Output table
# ---------------------------------------------------------------------------

def _fmt(val: float | None, decimals: int = 1, unit: str = "") -> str:
    if val is None:
        return "—"
    return f"{val:.{decimals}f}{unit}"


def print_results(
    results: list[ModelResult],
    history: dict[str, HistoricalData],
    show_vram: bool,
) -> None:
    ok = sorted(
        [r for r in results if not r.error and r.samples],
        key=lambda r: r.median_tok_per_sec() or 0.0,
        reverse=True,
    )
    err = [r for r in results if r.error or not r.samples]

    col_m = max((len(r.model) for r in results), default=5)
    col_m = max(col_m, 20)

    cols = [
        (f"{'Model':<{col_m}}", col_m, "<"),
        ("Provider",   10, "<"),
        ("TTFT p50",   10, ">"),
        ("Tok/s p50",  10, ">"),
        ("Lat p50",     9, ">"),
        ("Lat p95",     9, ">"),
    ]
    if history:
        cols += [("Hist p50", 10, ">"), ("Hist t/s", 10, ">")]
    if show_vram:
        cols.append(("VRAM", 9, ">"))

    def row_str(cells: list[str]) -> str:
        return "  ".join(
            f"{c:{align}{w}}" for (_, w, align), c in zip(cols, cells)
        )

    header_cells = [label for label, _, _ in cols]
    header = row_str(header_cells)

    print()
    print(header)
    print("─" * len(header))

    for r in ok:
        h = history.get(r.model)
        cells = [
            r.model,
            r.provider,
            _fmt(r.p50("ttft_ms"), 0, " ms"),
            _fmt(r.median_tok_per_sec(), 1, " t/s"),
            _fmt(r.p50("total_ms"), 0, " ms"),
            _fmt(r.p95("total_ms"), 0, " ms"),
        ]
        if history:
            cells += [
                _fmt(h.p50_ms if h else None, 0, " ms"),
                _fmt(h.avg_tok_per_sec if h else None, 1, " t/s"),
            ]
        if show_vram:
            vram_str = f"{r.vram_mb / 1024:.1f} GB" if r.vram_mb else "—"
            cells.append(vram_str)
        print(row_str(cells))

    for r in err:
        print(f"  {r.model:<{col_m}}  ERROR: {r.error or 'no samples collected'}")

    print()
    total = sum(len(r.samples) for r in ok)
    print(f"Total samples: {total}  ({len(ok)} model(s) OK, {len(err)} failed)")


# ---------------------------------------------------------------------------
# Cloud confirmation
# ---------------------------------------------------------------------------

def confirm_cloud(models: list[tuple[str, str]], yes: bool) -> bool:
    """Warn and prompt if any selected models route to cloud APIs. Returns False to abort."""
    cloud = [(name, prov) for name, prov in models if prov != "ollama"]
    if not cloud:
        return True
    if yes:
        return True

    by_prov: dict[str, list[str]] = {}
    for name, prov in cloud:
        by_prov.setdefault(prov, []).append(name)

    print("\nWARNING: the following models will call cloud APIs and incur cost:")
    for prov in sorted(by_prov):
        print(f"  {prov}: {', '.join(by_prov[prov])}")
    print()

    try:
        answer = input("Continue? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--key", default=os.environ.get("LITELLM_KEY", ""))
    p.add_argument("--host", default=os.environ.get("LITELLM_HOST", "http://localhost:4000"))
    p.add_argument("--models", default="", help="Comma-separated model names")
    p.add_argument("--all", action="store_true", help="Include cloud providers")
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--no-vram", action="store_true")
    p.add_argument("--no-history", action="store_true")
    p.add_argument("--db-url", default="")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation for cloud models")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    stack_dir = Path(__file__).parent.parent
    load_env(stack_dir / ".env")

    # Re-check env after loading .env
    if not args.key:
        args.key = os.environ.get("LITELLM_KEY", "")
    if not args.key:
        print("ERROR: --key or LITELLM_KEY required (create one at http://localhost:4000/ui)", file=sys.stderr)
        sys.exit(1)

    config_path = stack_dir / "observability" / "litellm" / "config.yaml"
    config_models = parse_config_models(config_path)
    if not config_models:
        print(f"WARNING: could not parse models from {config_path}", file=sys.stderr)

    models = select_models(args, config_models)
    if not models:
        what = "--all or --models" if not args.all else "any configured ollama models"
        print(f"No models to benchmark. Use {what}.", file=sys.stderr)
        sys.exit(1)

    if not confirm_cloud(models, args.yes):
        print("Aborted.")
        sys.exit(0)

    track_vram = not args.no_vram
    if track_vram and read_vram_mb() is None:
        print("Note: nvidia-smi unavailable — VRAM tracking disabled.")
        track_vram = False

    db_url = args.db_url or os.environ.get("DATABASE_URL", "")
    history: dict[str, HistoricalData] = {}
    if not args.no_history:
        if db_url:
            print("Querying LiteLLM_SpendLogs for 30-day historical baseline...", end=" ", flush=True)
            history = query_history(db_url)
            if history:
                print(f"{len(history)} model(s) with history.")
            else:
                print("none found (psycopg2 missing, no data, or schema mismatch).")
        else:
            print("Note: DATABASE_URL not set — skipping historical comparison.")

    provider_summary = {}
    for _, prov in models:
        provider_summary[prov] = provider_summary.get(prov, 0) + 1
    prov_str = ", ".join(f"{n} {p}" for p, n in sorted(provider_summary.items()))

    print(f"\nBenchmarking {len(models)} model(s) [{prov_str}]")
    print(f"  {args.runs} run(s) × {len(PROMPTS)} prompts = {args.runs * len(PROMPTS)} samples per model")
    print(f"  Host: {args.host}\n")

    results: list[ModelResult] = []
    for model_name, provider in models:
        r = run_model(
            host=args.host,
            key=args.key,
            model=model_name,
            provider=provider,
            runs=args.runs,
            timeout=args.timeout,
            track_vram=track_vram,
        )
        results.append(r)

    print_results(results, history, track_vram)

    if db_url:
        write_results(db_url, results)


if __name__ == "__main__":
    main()

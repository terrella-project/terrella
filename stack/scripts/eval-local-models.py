#!/usr/bin/env python3
"""Evaluate local ollama models for each role the stack serves.

The throughput benchmark (benchmark-models.py) says how fast a model is. This
script says how good it is at the job a role gives it, and how fast it does
that job, so a model can be picked for each role from data:

  fim      tab completion: fill a hole between a prefix and a suffix
  reason   "think it through": problems with one checkable answer
  general  summaries and log triage: required facts, no invented ones
  code     write a function that passes hidden tests (run in a sandbox)
  embed    retrieval over this repo's docs: does the query find its section
  agent    an agent harness's tool loop at 64k context, through ollama's
           Anthropic-format endpoint: right tool, right arguments, an answer
           from the tool's result, no tool call when none is needed

It talks to ollama's native API directly, not through the gateway, because
only the native API says how many tokens a reply took and how long the model
spent on them, and whether the model sits wholly on the GPU.

The task sets live in stack/eval/<role>/. `selfcheck` runs every answer key
through the same graders the models face, and must pass before a result is
trusted. See docs/operations/benchmarking.md.

Exit status: 0 clean; 2 when a cell carries a warning (the model spilled off
the GPU, a reply was cut off by the token limit or came back empty); 1 when a
cell is incomplete or a request failed. A number from a warned or incomplete
cell is printed with its flag and must not be quoted without it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO / "stack" / "eval"
ROLES = ("fim", "reason", "general", "code", "embed", "agent")

DEFAULT_MODELS = {
    "fim": [
        "qwen2.5-coder:1.5b",
        "qwen2.5-coder:3b",
        "qwen2.5-coder:7b",
        "starcoder2:3b",
        "codegemma:2b-code",
        "granite-code:3b",
    ],
    "reason": [
        "deepseek-r1:14b",
        "gpt-oss:20b",
        "gemma4:12b",
        "ornith-1.5:9b",
        "mimo-v2.6:9b",
        "nemotron-3.5-bolt:e4b",
        "bonsai-2:27b",
    ],
    "general": [
        "gemma2:9b",
        "lfm3:1.7b",
        "deepseek-r1:14b",
        "gpt-oss:20b",
        "gemma4:12b",
        "ornith-1.5:9b",
        "mimo-v2.6:9b",
        "nemotron-3.5-bolt:e4b",
        "bonsai-2:27b",
    ],
    "code": [
        "qwen2.5-coder:14b",
        "devstral:24b",
        "gpt-oss:20b",
        "mimo-v2.6:9b",
        "ornith-1.5:9b",
        "gemma4:12b",
    ],
    "embed": [
        "nomic-embed-text",
        "nomic-embed-text-v2-moe",
        "embeddinggemma-2",
        "qwen3-embedding",
    ],
    # The <model>-64k variants provision/sync-models.sh makes from
    # provision/agent-models.list (or by hand for a candidate).
    "agent": [
        "ornith-1.5:9b-64k",
        "mimo-v2.6:9b-64k",
        "ornith:9b-64k",
        "nemotron-3.5-bolt:e4b-64k",
        "lfm3:1.7b-64k",
        "bonsai-2:27b-64k",
        "gpt-oss:20b-64k",
    ],
}

# Per-role request settings. num_predict for reason is large on purpose: a
# thinking model spends tokens before its answer, and a limit that cuts the
# thinking off scores a model 0 for a reason that has nothing to do with it
# (deepseek-r1 in the July baseline).
ROLE_OPTIONS = {
    "fim": {"num_predict": 64, "num_ctx": 4096},
    "reason": {"num_predict": 12288, "num_ctx": 16384},
    "general": {"num_predict": 3072, "num_ctx": 16384},
    "code": {"num_predict": 6144, "num_ctx": 16384},
    "agent": {"max_tokens": 4096},  # the context comes from the -64k variant
}

# Documented query/document prefixes for the embedding models (each model's
# ollama library page). embeddinggemma-2's page names task prefixes without
# giving them; the embeddinggemma ones are used, and the plain variant is run
# beside it so the choice shows in the numbers.
EMBED_VARIANTS = {
    "nomic-embed-text": [("prefixed", "search_query: ", "search_document: ")],
    "nomic-embed-text-v2-moe": [("prefixed", "search_query: ", "search_document: ")],
    "embeddinggemma-2": [
        ("prefixed", "task: search result | query: ", "title: none | text: "),
        ("plain", "", ""),
    ],
    "qwen3-embedding": [
        (
            "instruct",
            (
                "Instruct: Given a question about a self-hosted AI stack, retrieve the "
                "documentation section that answers it\nQuery: "
            ),
            "",
        )
    ],
}
CHUNK_CHARS = 1200  # stays under nomic-embed-text-v2-moe's 512-token input

SANDBOX_IMAGE = os.environ.get("EVAL_SANDBOX_IMAGE", "docker.io/library/python:3.12-slim-bookworm")
SANDBOX_TIMEOUT_S = 10

# Statuses. PASS/FAIL are verdicts; the rest say why a sample has none.
PASS, FAIL = "pass", "fail"
TRUNCATED, EMPTY, UNPARSABLE, ERROR = "truncated", "empty", "unparsable", "error"
WARN_STATUSES = {TRUNCATED, EMPTY}


# ---------------------------------------------------------------------------
# ollama client
# ---------------------------------------------------------------------------


class OllamaError(RuntimeError):
    pass


class Ollama:
    def __init__(self, host: str, timeout: float = 900.0):
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _req(self, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            self.host + path,
            data=data,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="GET" if body is None else "POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            raise OllamaError(f"{path}: HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise OllamaError(f"{path}: {e}") from e

    def version(self) -> str:
        return self._req("/api/version").get("version", "?")

    def digests(self) -> dict[str, str]:
        out = {}
        for m in self._req("/api/tags").get("models", []):
            out[m["name"]] = m.get("digest", "?")
        return out

    def ps(self) -> list[dict]:
        return self._req("/api/ps").get("models", [])

    def unload(self, model: str) -> None:
        self._req("/api/generate", {"model": model, "keep_alive": 0})

    def generate(self, **body) -> dict:
        return self._req("/api/generate", {"stream": False, **body})

    def chat(self, **body) -> dict:
        return self._req("/api/chat", {"stream": False, **body})

    def messages(self, **body) -> dict:
        """ollama's Anthropic-format endpoint, the one an agent harness uses."""
        return self._req(
            "/v1/messages", body, {"x-api-key": "ollama", "anthropic-version": "2023-06-01"}
        )

    def embed(self, model: str, inputs: list[str]) -> dict:
        return self._req("/api/embed", {"model": model, "input": inputs, "keep_alive": "10m"})


def canonical(name: str) -> str:
    return name if ":" in name else name + ":latest"


def nvidia_used_mib() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
        return int(out.split()[0])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def gpu_identity() -> str:
    try:
        return subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "?"


def mem_available_gb() -> float | None:
    """MemAvailable from /proc/meminfo, in GB (None where there is none)."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1048576
    except OSError:
        return None
    return None


def wait_for_memory(
    min_gb: float,
    max_wait_s: float = 1800.0,
    poll_s: float = 30.0,
    reader=mem_available_gb,
    sleep=time.sleep,
) -> tuple[bool, float | None]:
    """Wait until at least min_gb of RAM is available, so loading a model does
    not push a busy machine into the OOM killer (it took ollama's runner once,
    mid-run). Returns (ok, last reading); ok is False after max_wait_s."""
    waited = 0.0
    while True:
        free = reader()
        if free is None or free >= min_gb:
            return True, free
        if waited >= max_wait_s:
            return False, free
        sleep(poll_s)
        waited += poll_s


def clear_card(client: Ollama, wait_s: float = 60.0) -> None:
    """Unload every model and wait until ollama reports none loaded."""
    for m in client.ps():
        client.unload(m["name"])
    deadline = time.monotonic() + wait_s
    while client.ps():
        if time.monotonic() > deadline:
            names = ", ".join(m["name"] for m in client.ps())
            raise OllamaError(f"models still loaded after {wait_s:.0f}s: {names}")
        time.sleep(1)
    time.sleep(2)  # let the driver hand the memory back before the baseline


def residency(client: Ollama, model: str) -> dict:
    """What ollama says about the loaded model: size, how much is on the GPU,
    and whether anything else shares the card."""
    loaded = client.ps()
    me = [m for m in loaded if canonical(m["name"]) == canonical(model)]
    others = [m["name"] for m in loaded if canonical(m["name"]) != canonical(model)]
    if not me:
        return {"loaded": False, "others": others}
    size, vram = me[0].get("size", 0), me[0].get("size_vram", 0)
    return {
        "loaded": True,
        "size": size,
        "size_vram": vram,
        "spilled": vram < size,
        "context": me[0].get("context_length"),
        "others": others,
    }


# ---------------------------------------------------------------------------
# Graders (pure functions: the unit tests and selfcheck exercise these)
# ---------------------------------------------------------------------------


def norm_digits(s: str) -> str:
    """Drop the thin and no-break spaces some models put between digit groups
    ("5\u202f069"), so 5069 written either way grades the same."""
    return re.sub(r"(?<=\d)[\u00a0\u2009\u202f](?=\d)", "", s or "")


def norm_line(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def nonblank_lines(s: str) -> list[str]:
    return [ln for ln in s.splitlines() if ln.strip()]


def fim_cut(task: dict, completion: str) -> str:
    """The completion cut to as many non-blank lines as the hole had.

    A FIM model keeps writing after the hole (often repeating the suffix);
    an editor shows the first lines, so those are what is graded."""
    k = len(nonblank_lines(task["expected"]))
    out, seen = [], 0
    for ln in completion.splitlines(keepends=True):
        out.append(ln)
        if ln.strip():
            seen += 1
            if seen == k:
                break
    text = "".join(out)
    return text if text.endswith("\n") else text + "\n"


def fim_line_match(task: dict, completion: str) -> bool:
    want = [norm_line(x) for x in nonblank_lines(task["expected"])]
    got = [norm_line(x) for x in nonblank_lines(fim_cut(task, completion))]
    return got == want


def grade_fim(
    task: dict, completion: str, done_reason: str | None, run_code=None
) -> tuple[str, dict]:
    """PASS when the cut completion matches the hole line for line, or (for a
    task with a test) when the program built from it passes the test."""
    if not completion.strip():
        return EMPTY, {}
    k = len(nonblank_lines(task["expected"]))
    if len(nonblank_lines(completion)) < k and done_reason == "length":
        return TRUNCATED, {}
    line_ok = fim_line_match(task, completion)
    detail = {"line_match": line_ok}
    if task.get("test") and run_code is not None:
        exec_ok = False
        for body in dict.fromkeys([fim_cut(task, completion), completion]):
            prog = task["prefix"] + body + task["suffix"] + "\n" + task["test"] + "\n"
            if run_code(prog)["ok"]:
                exec_ok = True
                break
        detail["exec_pass"] = exec_ok
        return (PASS if exec_ok or line_ok else FAIL), detail
    return (PASS if line_ok else FAIL), detail


ANSWER_RE = re.compile(
    r"^\W*(?:final\s+)?answer\W*\s*[:=]\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE
)


def parse_answer(content: str) -> str | None:
    found = ANSWER_RE.findall(norm_digits(content))
    if not found:
        return None
    return found[-1].strip().strip("*`").strip()


def _num(s: str) -> float | None:
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", s.replace("−", "-"))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.casefold()).strip()


def answer_correct(task: dict, value: str) -> bool:
    keys = task["answer"] if isinstance(task["answer"], list) else [task["answer"]]
    kind = task.get("answer_type", "text")
    for key in keys:
        if kind in ("int", "decimal"):
            got, want = _num(value), _num(str(key))
            if got is None or want is None:
                continue
            tol = 0.0 if kind == "int" else max(1e-6, abs(want) * 1e-4, 0.005)
            if abs(got - want) <= tol:
                return True
        elif _text(value) == _text(str(key)):
            return True
    return False


def grade_reason(task: dict, content: str, done_reason: str | None) -> tuple[str, dict]:
    value = parse_answer(content)
    if value is None:
        if done_reason == "length":
            return TRUNCATED, {}
        if not (content or "").strip():
            return EMPTY, {}
        return UNPARSABLE, {}
    return (PASS if answer_correct(task, value) else FAIL), {"answer": value}


def grade_general(task: dict, content: str, done_reason: str | None) -> tuple[str, dict]:
    """PASS when every required fact is present and no forbidden one is.

    The score is a screen, not the verdict: a report can name every required
    fact and still invent others the list does not foresee, so each reply is
    also read by a person before a model is picked."""
    if done_reason == "length":
        return TRUNCATED, {}
    if not (content or "").strip():
        return EMPTY, {}
    content = norm_digits(content)
    missing, invented = [], []
    for group in task["required"]:
        alts = group if isinstance(group, list) else [group]
        if not any(re.search(a, content, re.IGNORECASE) for a in alts):
            missing.append(alts[0])
    for pat in task.get("forbidden", []):
        if re.search(pat, content, re.IGNORECASE):
            invented.append(pat)
    total = len(task["required"])
    detail = {"facts": f"{total - len(missing)}/{total}", "missing": missing, "invented": invented}
    return (PASS if not missing and not invented else FAIL), detail


CODE_BLOCK_RE = re.compile(r"```[ \t]*(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code(content: str) -> str | None:
    blocks = CODE_BLOCK_RE.findall(content or "")
    if blocks:
        return max(blocks, key=len)
    if re.search(r"^\s*def \w+\(", content or "", re.MULTILINE):
        return content
    return None


def grade_code(task: dict, content: str, done_reason: str | None, run_code) -> tuple[str, dict]:
    if not (content or "").strip():
        # A thinking model that spends the whole budget thinking leaves no
        # answer: that is the limit's doing, so say so.
        return (TRUNCATED if done_reason == "length" else EMPTY), {}
    code = extract_code(content)
    if code is None:
        return (TRUNCATED if done_reason == "length" else UNPARSABLE), {}
    res = run_code(code + "\n\n" + task["tests"] + "\n")
    return (PASS if res["ok"] else FAIL), {"exit": res["exit"], "stderr": res["stderr"][-300:]}


def tool_uses(resp: dict) -> list[dict]:
    return [b for b in resp.get("content", []) if b.get("type") == "tool_use"]


def reply_text(resp: dict) -> str:
    return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")


AGENT_MAX_TURNS = 4


def agent_step(task: dict, resp: dict, state: dict) -> tuple[str | None, list | None]:
    """Grade one reply of the tool loop.

    Returns (status, None) when the reply ends the task, or (None, results)
    with the tool_result blocks to send back. The model passes when it calls
    expect_tool with arguments matching expect_args and then answers so the
    answer matches expect_final. On the way it may call any tool the task
    gives a `fallback` result for (checking that a file exists before reading
    it is caution, not a mistake); those calls are counted. A call to any
    other tool, wrong arguments to expect_tool, or an answer given without
    expect_tool fails. When expect_tool is null, any tool call fails."""
    calls = tool_uses(resp)
    state.setdefault("calls", []).extend(c.get("name") for c in calls)
    state.setdefault("extra", 0)
    if not calls:
        text = norm_digits(reply_text(resp))
        if not text.strip():
            return (TRUNCATED if resp.get("stop_reason") == "max_tokens" else EMPTY), None
        if task["expect_tool"] is not None and not state.get("hit"):
            state["step"] = "answered without using the tool"
            return FAIL, None
        state["step"] = "answer"
        ok = re.search(task["expect_final"], text, re.IGNORECASE) is not None
        return (PASS if ok else FAIL), None
    if task["expect_tool"] is None:
        state["step"] = "called a tool when none was needed"
        return FAIL, None
    fallback = task.get("fallback") or {}
    results = []
    for c in calls:
        name, args = c.get("name"), json.dumps(c.get("input", {}))
        if name == task["expect_tool"]:
            if not re.search(task["expect_args"], args, re.IGNORECASE):
                state["step"], state["args"] = "wrong arguments", args
                return FAIL, None
            state["hit"] = True
            content = task["tool_result"]
        elif name in fallback:
            state["extra"] += 1
            content = fallback[name]
        else:
            state["step"], state["args"] = f"called {name}, which cannot help", args
            return FAIL, None
        results.append({"type": "tool_result", "tool_use_id": c.get("id"), "content": content})
    return None, results


# ---------------------------------------------------------------------------
# Sandbox for model-written code
# ---------------------------------------------------------------------------

_sandbox_n = 0


def run_in_sandbox(code: str, image: str = SANDBOX_IMAGE) -> dict:
    """Run Python from a model in a throwaway container with no network.

    The container has an exact name so a stuck one can be removed by name
    (never by a prune on a shared machine)."""
    global _sandbox_n
    _sandbox_n += 1
    name = f"tml-eval-{os.getpid()}-{_sandbox_n}"
    cmd = [
        "podman",
        "run",
        "--rm",
        "-i",
        "--name",
        name,
        "--network",
        "none",
        "--memory",
        "512m",
        "--pids-limit",
        "64",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--user",
        "65534:65534",
        "--workdir",
        "/tmp",
        image,
        "timeout",
        str(SANDBOX_TIMEOUT_S),
        "python3",
        "-I",
        "-",
    ]
    try:
        p = subprocess.run(
            cmd,
            input=code,
            capture_output=True,
            text=True,
            check=False,
            timeout=SANDBOX_TIMEOUT_S + 60,
        )
        return {
            "ok": p.returncode == 0,
            "exit": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except subprocess.TimeoutExpired:
        subprocess.run(["podman", "rm", "-f", name], capture_output=True, check=False)
        return {"ok": False, "exit": -1, "stdout": "", "stderr": "sandbox timeout"}


# ---------------------------------------------------------------------------
# Task sets
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {
    "fim": {"id", "lang", "source", "prefix", "suffix", "expected", "test"},
    "reason": {"id", "category", "prompt", "answer", "answer_type", "solution"},
    "general": {"id", "prompt", "input", "required", "forbidden"},
    "code": {"id", "prompt", "entry", "tests", "reference"},
    "agent": {"id", "tools", "prompt", "expect_tool", "expect_args", "tool_result", "expect_final"},
}


def task_path(role: str) -> Path:
    return EVAL_DIR / role / ("queries.jsonl" if role == "embed" else "tasks.jsonl")


def load_tasks(role: str) -> list[dict]:
    path = task_path(role)
    tasks = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip():
            try:
                tasks.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{n}: {e}") from e
    return tasks


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def validate_tasks(role: str, tasks: list[dict]) -> list[str]:
    problems = []
    ids = [t.get("id") for t in tasks]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        problems.append(f"{role}: duplicate ids {sorted(dupes)}")
    need = REQUIRED_FIELDS.get(role, {"id", "query", "expect"})
    for t in tasks:
        missing = need - set(t)
        if missing:
            problems.append(f"{role}/{t.get('id')}: missing {sorted(missing)}")
    if not tasks:
        problems.append(f"{role}: no tasks")
    return problems


# ---------------------------------------------------------------------------
# Embedding corpus: this repo's docs at a pinned commit
# ---------------------------------------------------------------------------


def corpus_ref() -> str:
    return (EVAL_DIR / "embed" / "corpus-ref").read_text().split()[0]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    ).stdout


def _heading_text(line: str) -> str:
    text = line.lstrip("#").strip()
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)


def chunk_markdown(path: str, text: str, limit: int = CHUNK_CHARS) -> list[dict]:
    """Split a document at its H1/H2 headings (outside code fences); split a
    long section further at blank lines. A chunk's section is
    "<path>#<heading>"; retrieval is scored by section."""
    sections, cur_head, cur, fence = [], "(top)", [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        if not fence and re.match(r"^#{1,2} \S", line):
            if "".join(cur).strip():
                sections.append((cur_head, cur))
            cur_head, cur = _heading_text(line), [line]
        else:
            cur.append(line)
    if "".join(cur).strip():
        sections.append((cur_head, cur))

    chunks = []
    for head, lines in sections:
        section = f"{path}#{head}"
        paras = re.split(r"\n\s*\n", "\n".join(lines).strip())
        parts, buf = [], ""
        for p in paras:
            while len(p) > limit:  # one huge paragraph or table
                if buf:
                    parts.append(buf)
                    buf = ""
                parts.append(p[:limit])
                p = p[limit:]
            if buf and len(buf) + len(p) + 2 > limit:
                parts.append(buf)
                buf = p
            else:
                buf = f"{buf}\n\n{p}" if buf else p
        if buf.strip():
            parts.append(buf)
        for i, body in enumerate(parts):
            cid = section if len(parts) == 1 else f"{section} [{i + 1}]"
            chunks.append({"id": cid, "section": section, "text": body})
    return chunks


def load_corpus(ref: str | None = None) -> list[dict]:
    ref = ref or corpus_ref()
    names = [
        n
        for n in _git("ls-tree", "-r", "--name-only", ref).splitlines()
        if (n.startswith("docs/") and n.endswith(".md")) or n in ("README.md", "ROADMAP.md")
    ]
    chunks = []
    for n in sorted(names):
        chunks.extend(chunk_markdown(n, _git("show", f"{ref}:{n}")))
    return chunks


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def rank_sections(qvec: list[float], chunks: list[dict], dvecs: list[list[float]]) -> list[str]:
    best: dict[str, float] = {}
    for c, v in zip(chunks, dvecs, strict=True):
        s = cosine(qvec, v)
        if s > best.get(c["section"], -2.0):
            best[c["section"]] = s
    return sorted(best, key=lambda k: -best[k])


def retrieval_metrics(ranked: list[list[str]], expects: list[list[str]]) -> dict:
    r1 = r5 = rr = 0.0
    for order, want in zip(ranked, expects, strict=True):
        pos = next((i for i, s in enumerate(order) if s in want), None)
        if pos is not None:
            r1 += pos == 0
            r5 += pos < 5
            rr += 1.0 / (pos + 1)
    n = len(expects) or 1
    return {"recall@1": r1 / n, "recall@5": r5 / n, "mrr": rr / n}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))]


def timed(fn):
    """Run fn; also report whether the machine slept during it.

    time.monotonic() stops while the machine is suspended and time.time() does
    not, so a gap between them means the sample's timings are not real."""
    w0, m0 = time.time(), time.monotonic()
    out = fn()
    slept = (time.time() - w0) - (time.monotonic() - m0)
    return out, slept


def sample_record(
    task_id: str,
    status: str,
    detail: dict,
    resp: dict | None,
    output: str,
    thinking: str = "",
    slept: float = 0.0,
) -> dict:
    resp = resp or {}
    rec = {
        "task": task_id,
        "status": status,
        **detail,
        "output": output,
        "thinking_chars": len(thinking or ""),
        # enough to see whether a model that ran out of budget was looping
        "thinking_tail": (thinking or "")[-1500:],
        "done_reason": resp.get("done_reason"),
        "eval_count": resp.get("eval_count"),
        "eval_ns": resp.get("eval_duration"),
        "prompt_eval_ns": resp.get("prompt_eval_duration"),
        "load_ns": resp.get("load_duration"),
        "total_ns": resp.get("total_duration"),
    }
    if slept > 5:
        rec["status"], rec["error"] = ERROR, f"machine slept {slept:.0f}s mid-sample"
    return rec


MIN_SPEED_TOKENS = 8  # a reply of one or two tokens has no meaningful rate


def speed_samples(samples: list[dict]) -> list[float]:
    """Tokens per second from ollama's own counters, for replies long enough
    to have a rate. A one-token reply takes a few microseconds of eval time
    and would read as a million tokens a second."""
    return [
        s["eval_count"] / (s["eval_ns"] / 1e9)
        for s in samples
        if (s.get("eval_count") or 0) >= MIN_SPEED_TOKENS and s.get("eval_ns")
    ]


def summarize(samples: list[dict], n_expected: int) -> dict:
    statuses: dict[str, int] = {}
    for s in samples:
        statuses[s["status"]] = statuses.get(s["status"], 0) + 1
    tps = speed_samples(samples)
    lat = [(s["total_ns"] - (s.get("load_ns") or 0)) / 1e6 for s in samples if s.get("total_ns")]
    graded = [s for s in samples if s["status"] in (PASS, FAIL, UNPARSABLE)]
    return {
        "n_expected": n_expected,
        "n_done": len(samples),
        "pass": statuses.get(PASS, 0),
        "statuses": statuses,
        "tok_s_p50": statistics.median(tps) if tps else None,
        "tok_s_min": min(tps) if tps else None,
        "tok_s_max": max(tps) if tps else None,
        "tok_s_n": len(tps),
        "latency_ms_p50": pct(lat, 0.5),
        "latency_ms_p95": pct(lat, 0.95),
        "graded": len(graded),
    }


class Run:
    def __init__(
        self,
        client: Ollama,
        seed: int,
        runs: int,
        out: Path,
        think: str = "default",
        sampling: str = "greedy",
        min_free_gb: float = 0.0,
    ):
        self.client, self.seed, self.runs, self.out = client, seed, runs, out
        # "default" leaves thinking to the model; "off" sends think=false;
        # "low"/"medium"/"high" set gpt-oss's effort (it cannot turn it off).
        self.think = think
        # "greedy": temperature 0 (the default, so runs repeat); "model": the
        # model's own sampling settings from its Modelfile. Some thinking
        # models are published with a temperature near 1 and loop when greedy.
        self.sampling = sampling
        self.min_free_gb = min_free_gb
        self.cells: list[dict] = []
        digests = client.digests()
        self.meta = {
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "ollama": client.version(),
            "gpu": gpu_identity(),
            "seed": seed,
            "harness_sha256": file_sha256(Path(__file__)),
            "git_head": _git("rev-parse", "--short", "HEAD").strip(),
            "git_dirty": bool(_git("status", "--porcelain").strip()),
        }
        self.digests = digests

    def save(self) -> None:
        self.out.write_text(json.dumps({"meta": self.meta, "cells": self.cells}, indent=1))

    def start_model(self, role: str, model: str) -> dict:
        variant = [f"think={self.think}"] if self.think != "default" else []
        variant += [f"sampling={self.sampling}"] if self.sampling != "greedy" else []
        cell = {
            "role": role,
            "model": model,
            "flags": [],
            **(
                {"variant": " ".join(variant)}
                if variant and role in ("reason", "general", "code")
                else {}
            ),
            "digest": self.digests.get(canonical(model), "?"),
            "options": ROLE_OPTIONS.get(role, {}),
        }
        if canonical(model) not in self.digests:
            cell["flags"].append("NOT-INSTALLED")
            return cell
        clear_card(self.client)
        if self.min_free_gb:
            ok, free = wait_for_memory(self.min_free_gb)
            cell["mem_available_gb"] = None if free is None else round(free, 1)
            if not ok:
                print(
                    f"  skipped: {free:.1f} GB RAM available, needs {self.min_free_gb}", flush=True
                )
                cell["flags"].append("LOW-MEMORY")
                return cell
        cell["gpu_baseline_mib"] = nvidia_used_mib()
        return cell

    def check_residency(self, cell: dict, model: str) -> None:
        r = residency(self.client, model)
        cell["residency"] = r
        if not r["loaded"]:
            cell["flags"].append("NOT-LOADED")
        elif r["spilled"]:
            cell["flags"].append("SPILLED")
        if r.get("others"):
            cell["flags"].append("SHARED-CARD")
        used = nvidia_used_mib()
        if used is not None and cell.get("gpu_baseline_mib") is not None:
            cell["gpu_mib"] = used - cell["gpu_baseline_mib"]

    def finish(self, cell: dict, samples: list[dict], n_expected: int) -> None:
        cell["samples"] = samples
        cell["summary"] = summarize(samples, n_expected)
        st = cell["summary"]["statuses"]
        if cell["summary"]["n_done"] < n_expected or st.get(ERROR):
            cell["flags"].append("INCOMPLETE")
        for w in sorted(WARN_STATUSES):
            if st.get(w):
                cell["flags"].append(f"{w.upper()}x{st[w]}")
        self.cells.append(cell)
        self.save()

    def think_param(self) -> dict:
        if self.think == "default":
            return {}
        return {"think": False if self.think == "off" else self.think}

    def opts(self, role: str) -> dict:
        greedy = {"temperature": 0} if self.sampling == "greedy" else {}
        return {**greedy, "seed": self.seed, **ROLE_OPTIONS[role]}

    # -- roles --------------------------------------------------------------

    def role_fim(self, model: str, tasks: list[dict]) -> None:
        cell = self.start_model("fim", model)
        samples: list[dict] = []
        n_expected = len(tasks) * self.runs
        if not cell["flags"]:
            for rep in range(self.runs):
                for t in tasks:
                    try:
                        resp, slept = timed(
                            lambda t=t: self.client.generate(
                                model=model,
                                prompt=t["prefix"],
                                suffix=t["suffix"],
                                options=self.opts("fim"),
                                keep_alive="10m",
                            )
                        )
                    except OllamaError as e:
                        samples.append(
                            {"task": t["id"], "status": ERROR, "error": str(e), "rep": rep}
                        )
                        continue
                    text = resp.get("response", "")
                    # Quality is graded on the first pass; later passes are
                    # for speed, and say whether the replies stayed the same.
                    if rep == 0:
                        status, detail = grade_fim(t, text, resp.get("done_reason"), run_in_sandbox)
                    else:
                        first = next(
                            (
                                s
                                for s in samples
                                if s["task"] == t["id"]
                                and s.get("rep") == 0
                                and s["status"] != ERROR
                            ),
                            None,
                        )
                        if first is None:
                            status, detail = grade_fim(
                                t, text, resp.get("done_reason"), run_in_sandbox
                            )
                        else:
                            # Only the graded lines count: text past the hole
                            # is never shown, and varies more.
                            status, detail = (
                                first["status"],
                                {
                                    "same_as_first": fim_cut(t, text)
                                    == fim_cut(t, first.get("output", ""))
                                },
                            )
                    rec = sample_record(t["id"], status, detail, resp, text, slept=slept)
                    rec["rep"] = rep
                    samples.append(rec)
                    if rep == 0 and len(samples) == 1:
                        self.check_residency(cell, model)
        cell_samples = [s for s in samples if s.get("rep") == 0]
        self.finish(cell, samples, n_expected)
        cell["summary"]["pass"] = sum(s["status"] == PASS for s in cell_samples)
        cell["summary"]["line_match"] = sum(bool(s.get("line_match")) for s in cell_samples)
        cell["summary"]["graded"] = len(cell_samples)
        drift = [s for s in samples if s.get("same_as_first") is False]
        if drift:
            cell["flags"].append(f"NONDETERMINISTICx{len(drift)}")
        self.save()

    def _chat_role(self, role: str, model: str, tasks: list[dict], build, grade) -> None:
        cell = self.start_model(role, model)
        samples: list[dict] = []
        if not cell["flags"]:
            for t in tasks:
                try:
                    resp, slept = timed(
                        lambda t=t: self.client.chat(
                            model=model,
                            messages=build(t),
                            options=self.opts(role),
                            keep_alive="10m",
                            **self.think_param(),
                        )
                    )
                except OllamaError as e:
                    samples.append({"task": t["id"], "status": ERROR, "error": str(e)})
                    continue
                msg = resp.get("message", {})
                content, thinking = msg.get("content", ""), msg.get("thinking", "")
                status, detail = grade(t, content, resp.get("done_reason"))
                samples.append(
                    sample_record(t["id"], status, detail, resp, content, thinking, slept)
                )
                if len(samples) == 1:
                    self.check_residency(cell, model)
        self.finish(cell, samples, len(tasks))

    def role_reason(self, model: str, tasks: list[dict]) -> None:
        system = (
            "Solve the problem. Think as much as you need, then give the "
            "final answer on its own last line in exactly this form:\n"
            "ANSWER: <answer>\nGive only the value after ANSWER:, with no "
            "units unless the problem asks for them."
        )
        self._chat_role(
            "reason",
            model,
            tasks,
            lambda t: [
                {"role": "system", "content": system},
                {"role": "user", "content": t["prompt"]},
            ],
            grade_reason,
        )

    def role_general(self, model: str, tasks: list[dict]) -> None:
        self._chat_role(
            "general",
            model,
            tasks,
            lambda t: [{"role": "user", "content": t["prompt"] + "\n\n---\n" + t["input"]}],
            grade_general,
        )

    def role_code(self, model: str, tasks: list[dict]) -> None:
        self._chat_role(
            "code",
            model,
            tasks,
            lambda t: [{"role": "user", "content": t["prompt"]}],
            lambda t, c, d: grade_code(t, c, d, run_in_sandbox),
        )

    def role_agent(self, model: str, tasks: list[dict]) -> None:
        """Each task is a short tool loop in the Anthropic format (agent_step).

        The /v1/messages reply carries no timing, so speed is measured after
        the tool checks with one native chat on the same loaded model."""
        cell = self.start_model("agent", model)
        samples: list[dict] = []
        if not cell["flags"]:
            base = {
                "model": model,
                "temperature": 0,
                "max_tokens": ROLE_OPTIONS["agent"]["max_tokens"],
            }
            for t in tasks:
                msgs = [{"role": "user", "content": t["prompt"]}]
                state: dict = {}
                status, resp, slept = None, {}, 0.0
                try:
                    for _ in range(AGENT_MAX_TURNS):
                        resp, dt = timed(
                            lambda m=msgs, t=t: self.client.messages(
                                **base, tools=t["tools"], messages=m
                            )
                        )
                        slept += dt
                        status, results = agent_step(t, resp, state)
                        if status is not None:
                            break
                        msgs = [
                            *msgs,
                            {"role": "assistant", "content": resp["content"]},
                            {"role": "user", "content": results},
                        ]
                    else:
                        status = FAIL
                        state["step"] = f"no answer within {AGENT_MAX_TURNS} turns"
                except OllamaError as e:
                    samples.append({"task": t["id"], "status": ERROR, "error": str(e)})
                    continue
                detail = state
                rec = sample_record(t["id"], status, detail, None, reply_text(resp), slept=slept)
                rec["stop_reason"] = resp.get("stop_reason")
                samples.append(rec)
                if len(samples) == 1:
                    self.check_residency(cell, model)
            try:
                speed = self.client.chat(
                    model=model,
                    keep_alive="10m",
                    options={"temperature": 0, "seed": self.seed, "num_predict": 400},
                    messages=[
                        {
                            "role": "user",
                            "content": "Explain in about 300 words how a reverse proxy works.",
                        }
                    ],
                )
                cell["speed_sample"] = {
                    k: speed.get(k) for k in ("eval_count", "eval_duration", "done_reason")
                }
                if speed.get("eval_count") and speed.get("eval_duration"):
                    cell["tok_s"] = speed["eval_count"] / (speed["eval_duration"] / 1e9)
            except OllamaError as e:
                cell["speed_error"] = str(e)
        self.finish(cell, samples, len(tasks))
        if cell.get("tok_s"):
            cell["summary"]["tok_s_p50"] = cell["tok_s"]
            self.save()

    def role_embed(self, model: str, queries: list[dict]) -> None:
        chunks = load_corpus()
        for variant, qp, dp in EMBED_VARIANTS.get(model, [("plain", "", "")]):
            cell = self.start_model("embed", model)
            cell["variant"] = variant
            cell["corpus"] = {
                "ref": corpus_ref(),
                "chunks": len(chunks),
                "sections": len({c["section"] for c in chunks}),
            }
            if cell["flags"]:
                self.finish(cell, [], len(queries))
                continue
            try:
                dvecs, t0 = [], time.monotonic()
                for i in range(0, len(chunks), 32):
                    batch = [dp + c["text"] for c in chunks[i : i + 32]]
                    dvecs.extend(self.client.embed(model, batch)["embeddings"])
                    if i == 0:
                        self.check_residency(cell, model)
                cell["docs_per_s"] = len(chunks) / (time.monotonic() - t0)
                qvecs = self.client.embed(model, [qp + q["query"] for q in queries])["embeddings"]
            except OllamaError as e:
                self.finish(cell, [{"task": "*", "status": ERROR, "error": str(e)}], len(queries))
                continue
            ranked = [rank_sections(v, chunks, dvecs) for v in qvecs]
            samples = []
            for q, order in zip(queries, ranked, strict=True):
                pos = next((i for i, s in enumerate(order) if s in q["expect"]), None)
                samples.append(
                    {
                        "task": q["id"],
                        "status": PASS if pos == 0 else FAIL,
                        "rank": None if pos is None else pos + 1,
                        "top3": order[:3],
                    }
                )
            self.finish(cell, samples, len(queries))
            cell["summary"].update(retrieval_metrics(ranked, [q["expect"] for q in queries]))
            self.save()


# ---------------------------------------------------------------------------
# Self-check: the answer keys must pass the graders the models face
# ---------------------------------------------------------------------------


def selfcheck(roles: list[str]) -> int:
    problems: list[str] = []
    sections = None
    for role in roles:
        tasks = load_tasks(role)
        problems += validate_tasks(role, tasks)
        for t in tasks:
            tid = f"{role}/{t.get('id')}"
            if role == "fim":
                st, _ = grade_fim(
                    t, t["expected"], "stop", run_in_sandbox if t.get("test") else None
                )
                if st != PASS:
                    problems.append(f"{tid}: expected text does not pass ({st})")
                if t.get("test"):
                    prog = t["prefix"] + "    pass\n" + t["suffix"] + "\n" + t["test"]
                    if run_in_sandbox(prog)["ok"]:
                        problems.append(f"{tid}: test passes with `pass` in the hole")
            elif role == "reason":
                if t.get("solution"):
                    r = run_in_sandbox(t["solution"])
                    got = r["stdout"].strip().splitlines()[-1:] or [""]
                    if not r["ok"] or not answer_correct(t, got[0]):
                        problems.append(f"{tid}: solution printed {got[0]!r}, key {t['answer']!r}")
                st, _ = grade_reason(t, f"work...\nANSWER: {_first(t['answer'])}", "stop")
                if st != PASS:
                    problems.append(f"{tid}: key does not grade as correct")
            elif role == "code":
                st, d = grade_code(t, f"```python\n{t['reference']}\n```", "stop", run_in_sandbox)
                if st != PASS:
                    problems.append(f"{tid}: reference fails its tests: {d}")
                stub = f"def {t['entry']}(*a, **k):\n    return None\n"
                if run_in_sandbox(stub + "\n" + t["tests"])["ok"]:
                    problems.append(f"{tid}: tests pass against a stub")
            elif role == "general":
                for g in t["required"]:
                    for a in g if isinstance(g, list) else [g]:
                        re.compile(a)
                if t.get("reference"):
                    st, d = grade_general(t, t["reference"], "stop")
                    if st != PASS:
                        problems.append(f"{tid}: reference answer fails: {d}")
            elif role == "agent":
                names = {tool["name"] for tool in t["tools"]}
                if t["expect_tool"] is not None and t["expect_tool"] not in names:
                    problems.append(f"{tid}: expect_tool {t['expect_tool']!r} not offered")
                for fb in t.get("fallback") or {}:
                    if fb not in names or fb == t["expect_tool"]:
                        problems.append(f"{tid}: fallback {fb!r} is not another offered tool")
                for key in ("expect_args", "expect_final"):
                    if t.get(key):
                        re.compile(t[key])
                if t.get("reference_final") and not re.search(
                    t["expect_final"], t["reference_final"], re.IGNORECASE
                ):
                    problems.append(f"{tid}: reference_final does not match expect_final")
            elif role == "embed":
                if sections is None:
                    sections = {c["section"] for c in load_corpus()}
                for e in t["expect"]:
                    if e not in sections:
                        problems.append(f"{tid}: no section {e!r} in the corpus")
    for p in problems:
        print("PROBLEM", p)
    print(
        f"selfcheck {'FAILED' if problems else 'ok'}: {', '.join(roles)}"
        f" ({len(problems)} problem(s))"
    )
    return 1 if problems else 0


def _first(answer):
    return answer[0] if isinstance(answer, list) else answer


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def fmt(v, spec: str) -> str:
    return "-" if v is None else format(v, spec)


def print_report(cells: list[dict]) -> int:
    worst = 0
    for role in ROLES:
        rc = [c for c in cells if c["role"] == role]
        if not rc:
            continue
        print(f"\n== {role}")
        for c in rc:
            s = dict(c.get("summary", {}))
            tps = speed_samples(c.get("samples", []))
            if tps:
                s.update(tok_s_p50=statistics.median(tps), tok_s_min=min(tps), tok_s_max=max(tps))
            name = c["model"] + (f" [{c['variant']}]" if c.get("variant") else "")
            if role == "embed":
                score = (
                    f"r@1 {fmt(s.get('recall@1'), '.2f')}  r@5 "
                    f"{fmt(s.get('recall@5'), '.2f')}  mrr {fmt(s.get('mrr'), '.2f')}"
                    f"  {fmt(c.get('docs_per_s'), '.0f')} docs/s"
                )
            else:
                n = s.get("graded", 0) if role == "fim" else s.get("n_expected", 0)
                score = f"{s.get('pass', 0)}/{n}"
                if role == "fim":
                    score += f" (line {s.get('line_match', 0)})"
                score += (
                    f"  {fmt(s.get('tok_s_p50'), '.0f')} t/s"
                    f" [{fmt(s.get('tok_s_min'), '.0f')}-{fmt(s.get('tok_s_max'), '.0f')}]"
                    f"  p50 {fmt(s.get('latency_ms_p50'), '.0f')} ms"
                    f"  p95 {fmt(s.get('latency_ms_p95'), '.0f')} ms"
                )
            gpu = f"{c['gpu_mib']} MiB" if c.get("gpu_mib") is not None else "-"
            flags = " ".join(c.get("flags", []))
            print(f"  {name:<36} {score}  gpu {gpu}  {flags}")
            if any(f.startswith(("INCOMPLETE", "NOT-", "LOW-MEMORY")) for f in c.get("flags", [])):
                worst = 1
            elif c.get("flags") and worst == 0:
                worst = 2
    return worst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("role", choices=[*ROLES, "all", "selfcheck", "chunks", "report"])
    ap.add_argument("--models", help="comma-separated; default: the role's candidates")
    ap.add_argument("--host", default=os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434"))
    ap.add_argument("--runs", type=int, default=3, help="fim passes (speed); default 3")
    ap.add_argument("--seed", type=int, default=29)
    ap.add_argument(
        "--think",
        default="default",
        choices=["default", "off", "low", "medium", "high"],
        help="reason/general/code: thinking mode (default: the model's own)",
    )
    ap.add_argument(
        "--min-free-gb",
        type=float,
        default=12.0,
        help="wait (up to 30 min) for this much free RAM before loading "
        "each model, else skip it; 0 turns the check off",
    )
    ap.add_argument(
        "--sampling",
        default="greedy",
        choices=["greedy", "model"],
        help="reason/general/code: greedy (temperature 0) or the model's own",
    )
    ap.add_argument("--out", type=Path, help="results JSON (default: eval-<role>-<time>.json)")
    ap.add_argument("--roles", default=",".join(ROLES), help="for selfcheck/all: which roles")
    ap.add_argument("--results", type=Path, nargs="*", help="for report: result files")
    args = ap.parse_args()

    if args.role == "selfcheck":
        return selfcheck(args.roles.split(","))
    if args.role == "chunks":
        for c in load_corpus():
            print(c["id"])
        return 0
    if args.role == "report":
        cells = []
        for p in args.results or []:
            cells += json.loads(p.read_text())["cells"]
        return print_report(cells)

    roles = args.roles.split(",") if args.role == "all" else [args.role]
    out = args.out or Path(f"eval-{args.role}-{time.strftime('%Y%m%dT%H%M%S')}.json")
    client = Ollama(args.host)
    run = Run(client, args.seed, args.runs, out, args.think, args.sampling, args.min_free_gb)
    run.meta["think"], run.meta["sampling"] = args.think, args.sampling
    run.meta["task_sets"] = {r: file_sha256(task_path(r)) for r in roles}
    for role in roles:
        tasks = load_tasks(role)
        problems = validate_tasks(role, tasks)
        if problems:
            print("\n".join(problems))
            return 1
        models = args.models.split(",") if args.models else DEFAULT_MODELS[role]
        for m in models:
            print(f"[{time.strftime('%H:%M:%S')}] {role} {m}", flush=True)
            getattr(run, f"role_{role}")(m, tasks)
    clear_card(client)
    run.meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    run.save()
    print(f"\nresults: {out}")
    return print_report(run.cells)


if __name__ == "__main__":
    sys.exit(main())

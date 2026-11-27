"""Generate stack/eval/general/tasks.jsonl: edit the tasks here, not in the JSONL.

The inputs are synthetic, shaped on real terrella, ollama and LiteLLM output,
with the facts planted so they can be checked. `required` holds one list of
alternative patterns per fact; `forbidden` holds claims the input does not
support. `reference` is a correct answer; selfcheck grades it.

Run from the repo root:
    python3 stack/eval/general/make-tasks.py > stack/eval/general/tasks.jsonl
"""
import json
import subprocess

T = []


def task(id, prompt, input, required, forbidden, reference):
    T.append({"id": id, "prompt": prompt, "input": input.strip("\n") + "\n",
              "required": required, "forbidden": forbidden, "reference": reference})


task(
    "ollama-partial-offload",
    "Below is an excerpt from an ollama server log on a workstation with one 16 GB GPU. "
    "In at most five bullet points, say what went wrong and what the operator should do. "
    "Only state what the log shows.",
    """
time=2026-11-20T14:02:11.120-06:00 level=INFO source=server.go:412 msg="loaded model" model=qwen2.5-coder:14b size="9.7 GiB" layers.offload=49/49
time=2026-11-20T14:02:13.481-06:00 level=INFO source=routes.go:1630 msg="request" method=POST path=/api/chat status=200 duration=2.36s
time=2026-11-20T14:09:40.002-06:00 level=INFO source=sched.go:663 msg="gpu memory" id=0 library=CUDA available="5.4 GiB" free="5.9 GiB" minimum="457.0 MiB"
time=2026-11-20T14:09:40.010-06:00 level=INFO source=sched.go:702 msg="new model will fit partially in available VRAM" model=gemma4:12b required="8.6 GiB" available="5.4 GiB"
time=2026-11-20T14:09:40.512-06:00 level=INFO source=server.go:412 msg="loading model" model=gemma4:12b
load_tensors: offloading 27 repeating layers to GPU
load_tensors: offloaded 27/49 layers to GPU
load_tensors:          CPU model buffer size =  3521.40 MiB
load_tensors:        CUDA0 model buffer size =  4410.12 MiB
time=2026-11-20T14:09:52.877-06:00 level=INFO source=server.go:640 msg="llama runner started in 12.36 seconds"
time=2026-11-20T14:10:52.880-06:00 level=WARN source=routes.go:1645 msg="client disconnected" path=/api/chat error="context canceled" elapsed=60.0s
time=2026-11-20T14:10:52.881-06:00 level=INFO source=routes.go:1630 msg="request" method=POST path=/api/chat status=499 duration=1m0s
time=2026-11-20T14:11:30.214-06:00 level=INFO source=routes.go:1630 msg="request" method=GET path=/api/ps status=200 duration=310µs
""",
    [
        [r"27\s*/\s*49", r"partial(ly)?", r"not (all|fully)", r"\bCPU\b", r"spill"],
        [r"qwen2\.5-coder", r"(other|first|previous|already|another) (model|loaded)"],
        [r"(unload|evict|stop|free|keep_alive|one model at a time|smaller)"],
        [r"cancel", r"disconnect", r"time(d)?[ -]?out", r"\b499\b", r"60 ?s"],
    ],
    [r"out of memory", r"\bOOM\b", r"driver (crash|bug|update)", r"reinstall",
     r"(crash|crashed)"],
    "- gemma4:12b only fit partially: 27/49 layers on the GPU, the rest on the CPU.\n"
    "- qwen2.5-coder:14b was already loaded and held the VRAM.\n"
    "- The slow CPU-heavy model made the client disconnect after 60 s (context canceled, 499).\n"
    "- Unload qwen2.5-coder first (or lower keep_alive) so gemma4 fits wholly on the GPU.",
)

task(
    "litellm-start-noise",
    "This is the start log of an LLM gateway. For the operator, say briefly: is the gateway "
    "up, what is actually broken, and what is only noise?",
    """
15:48:41 - LiteLLM Proxy:INFO: proxy_server.py:2210 - Loading config from /app/config.yaml
15:48:43 - LiteLLM Proxy:WARNING: prisma_client.py:140 - Database connection failed (attempt 1/5): connection refused, retrying in 2s
15:48:45 - LiteLLM Proxy:INFO: prisma_client.py:152 - Connected to database
15:48:55 - LiteLLM Router:ERROR: router.py:6816 - Error creating deployment: litellm.BadRequestError: LLM Provider NOT provided. Pass in the LLM provider you are trying to call. You passed model=gpt-5-5
15:48:55 - LiteLLM Router:ERROR: router.py:6816 - Error creating deployment: litellm.BadRequestError: LLM Provider NOT provided. Pass in the LLM provider you are trying to call. You passed model=gpt-5-5-mini
15:48:56 - LiteLLM:WARNING: utils.py:765 - `litellm.set_verbose` is deprecated. Please set `os.environ['LITELLM_LOG'] = 'DEBUG'` for debug logs.
15:48:56 - LiteLLM:WARNING: utils.py:765 - `litellm.set_verbose` is deprecated. Please set `os.environ['LITELLM_LOG'] = 'DEBUG'` for debug logs.
15:48:57 - LiteLLM:WARNING: utils.py:765 - `litellm.set_verbose` is deprecated. Please set `os.environ['LITELLM_LOG'] = 'DEBUG'` for debug logs.
15:48:57 - LiteLLM:WARNING: utils.py:765 - `litellm.set_verbose` is deprecated. Please set `os.environ['LITELLM_LOG'] = 'DEBUG'` for debug logs.
15:48:58 - LiteLLM Proxy:INFO: proxy_server.py:3301 - Initialized 84 model deployments
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
""",
    [
        [r"\bup\b", r"running", r"listening", r"started", r"healthy"],
        [r"gpt-5-5"],
        [r"provider", r"prefix"],
        [r"set_verbose", r"deprecat"],
        [r"(database|db|postgres)[^\n]{0,160}(connected|retr|recover|succe|second attempt)",
         r"(retr|recover)[^\n]{0,80}(database|db|postgres)"],
    ],
    [r"gateway (is )?(down|not running|failed to start)", r"partial(ly)? (up|running|working)",
     r"database (is )?(down|unavailable|unreachable)\b(?![^.\n]{0,40}(briefly|at first|first attempt))",
     r"(anthropic|claude)[^.\n]{0,60}(fail|error|broken|down|refus)"],
    "The gateway is up (Uvicorn running on port 4000, 84 deployments). Broken: the gpt-5-5 and "
    "gpt-5-5-mini deployments were not created because the model has no provider prefix. "
    "Noise: the repeated set_verbose deprecation warnings, and the database retry, which "
    "connected on the second attempt.",
)

task(
    "changelog-announcement",
    "Write exactly three bullet points announcing this release to users of the project, "
    "one per change, in plain language.",
    """
## [0.4.0] - 2026-11-02

### Added

- **Budget alerts** (#211) — the gateway now emails the operator when a team passes 80% of
  its monthly budget. The threshold is set per team in `terrella.yaml` (`alert_at`).

### Changed

- **Prometheus retention** (#205) — metrics are now kept for 90 days instead of 15. Disk use
  grows by about 2 GB on a typical single-node install.

### Fixed

- **Open WebUI login loop** (#218) — signing in no longer bounces back to the login page when
  the browser blocks third-party cookies.
""",
    [
        [r"budget"],
        [r"80\s*%|80 percent"],
        [r"90 days|90-day"],
        [r"open webui|login|sign(ing)? in"],
    ],
    [r"\b30 days\b", r"slack", r"webhook", r"\b0\.5\b", r"(sms|text message)"],
    "- Budget alerts: the gateway emails you when a team passes 80% of its monthly budget.\n"
    "- Prometheus now keeps metrics for 90 days instead of 15 (about 2 GB more disk).\n"
    "- Fixed the Open WebUI login loop when third-party cookies are blocked.",
)

task(
    "diff-commit-message",
    "Write a conventional-commit message for this diff: a first line `type(scope): summary` "
    "in lower case, a blank line, then a short body. Return only the message.",
    """
diff --git a/stack/scripts/smoke.sh b/stack/scripts/smoke.sh
--- a/stack/scripts/smoke.sh
+++ b/stack/scripts/smoke.sh
@@ -8,6 +8,7 @@ set -euo pipefail
 HOST="${HOST:-http://127.0.0.1:4000}"
+TIMEOUT="${SMOKE_TIMEOUT:-30}"
 KEY="${LITELLM_KEY:?set LITELLM_KEY}"
@@ -21,7 +22,7 @@ check_model() {
   local model="$1"
-  curl -fsS "$HOST/v1/chat/completions" \\
+  curl -fsS --max-time "$TIMEOUT" "$HOST/v1/chat/completions" \\
     -H "Authorization: Bearer $KEY" \\
     -H 'Content-Type: application/json' \\
     -d "{\\"model\\":\\"$model\\",\\"messages\\":[{\\"role\\":\\"user\\",\\"content\\":\\"ping\\"}],\\"max_tokens\\":1}"
""",
    [
        [r"(?m)^\W*(feat|fix|chore|refactor)(\([\w./-]+\))?!?: [a-z]"],
        [r"time ?out|max-time"],
        [r"\b30\b", r"SMOKE_TIMEOUT"],
    ],
    [r"retr(y|ies)", r"test(s)? (added|pass)", r"--connect-timeout", r"\b60\b"],
    "fix(smoke): stop each model check after a timeout\n\n"
    "curl now runs with --max-time, so a hung model fails the check instead of blocking the "
    "script. The limit is SMOKE_TIMEOUT seconds, 30 by default.",
)

task(
    "podman-ps-triage",
    "Here is `podman ps -a` from the stack's host. Which containers need attention, and why? "
    "Be brief; do not list the healthy ones.",
    """
CONTAINER ID  IMAGE                                   COMMAND               CREATED       STATUS                     PORTS                     NAMES
3f1a2b9c0d11  docker.io/library/postgres:17           postgres              6 days ago    Up 6 days (healthy)        127.0.0.1:5433->5432/tcp  terrella-postgres
8c7d6e5f4a22  ghcr.io/berriai/litellm:main-v1.83.14   --config /app/con...  6 days ago    Up 6 days (healthy)        0.0.0.0:4000->4000/tcp    terrella-litellm
1b2c3d4e5f33  docker.io/grafana/grafana:12.3          grafana server        6 days ago    Up 6 days                  0.0.0.0:3000->3000/tcp    terrella-grafana
9a8b7c6d5e44  docker.io/prom/prometheus:v3.7          --config.file=/et...  6 days ago    Exited (137) 3 hours ago                             terrella-prometheus
5e4d3c2b1a55  ghcr.io/open-webui/open-webui:0.9.2     bash start.sh         6 days ago    Up 2 hours (unhealthy)     0.0.0.0:8080->8080/tcp    terrella-openwebui
7f6e5d4c3b66  localhost/litellm-exporter:latest       python3 /app/expo...  6 days ago    Up 6 days                  127.0.0.1:9101->9101/tcp  terrella-litellm-exporter
""",
    [
        [r"prometheus"],
        [r"\b137\b", r"SIGKILL", r"kill(ed)?", r"OOM|out of memory"],
        [r"open-?webui"],
        [r"unhealthy|health ?check"],
    ],
    [r"(postgres|grafana|exporter)[^\n]{0,60}(unhealthy|exited|stopped|down|failing)",
     r"litellm[^-\n][^\n]{0,60}(unhealthy|exited|stopped|down|failing)"],
    "- terrella-prometheus exited 3 hours ago with code 137 (killed by SIGKILL, often the "
    "OOM killer): restart it and check its memory limit.\n"
    "- terrella-openwebui is up but unhealthy: its health check is failing; check its logs.",
)

adr = subprocess.run(["git", "show",
                      "e450b7a:docs/adr/ADR-0003-gateway-litellm-behind-driver-boundary.md"],
                     capture_output=True, text=True, check=True).stdout
task(
    "adr-two-sentences",
    "Summarise this architecture decision in two sentences for someone new to the project.",
    adr,
    [
        [r"litellm"],
        [r"keep|stay|remain|retain"],
        [r"boundary|driver|isolat|abstract|view"],
        [r"swap|replac|switch|migrat|alternative|spike"],
    ],
    [r"tensorzero (was|is|has been) (chosen|adopted|selected)",
     r"(replaced|replaces|replacing) litellm with", r"bifrost (was|is) (chosen|adopted)"],
    "The project keeps LiteLLM as its gateway but isolates it behind a driver and SQL views, "
    "so nothing else reads LiteLLM's tables. That keeps a later swap cheap, and a time-boxed "
    "spike will weigh alternatives such as TensorZero.",
)

task(
    "timers-next-and-never",
    "From this `systemctl --user list-timers` output: which job runs next, and which job has "
    "never run? Answer in two short sentences.",
    """
NEXT                            LEFT          LAST                            PASSED       UNIT                          ACTIVATES
Fri 2026-11-27 12:15:00 CST     11min         Fri 2026-11-27 12:00:02 CST     3min ago     agent-backlog.timer           agent-backlog.service
Sat 2026-11-28 06:00:00 CST     17h           Fri 2026-11-27 06:00:04 CST     6h ago       issue-triage.timer            issue-triage.service
Sun 2026-11-29 18:00:00 CST     2 days        -                               -            earth-services-report.timer   earth-services-report.service
Mon 2026-11-30 07:00:00 CST     2 days        Mon 2026-11-23 07:00:01 CST     4 days ago   weekly-spend-report.timer     weekly-spend-report.service

4 timers listed.
""",
    [
        [r"agent-backlog"],
        [r"earth-services-report"],
        [r"never|not (yet )?run|no (previous|last) run|hasn'?t run"],
    ],
    [r"weekly-spend-report[^.\n]{0,40}never", r"issue-triage[^.\n]{0,40}never"],
    "agent-backlog runs next, at 12:15 today. earth-services-report has never run.",
)

task(
    "weekly-spend-note",
    "This CSV is one week of API spend per gateway key, in US dollars. Write a three-sentence "
    "note for the owner: the week's total, the key that spent the most, and anything unusual.",
    """
date,key,spend_usd
2026-11-16,repo-review,1.20
2026-11-16,weekly-brief,0.31
2026-11-17,repo-review,0.95
2026-11-17,issue-triage,0.22
2026-11-18,repo-review,1.10
2026-11-18,issue-triage,0.25
2026-11-19,docs-drift,7.85
2026-11-19,issue-triage,0.24
2026-11-20,repo-review,1.05
2026-11-20,issue-triage,0.21
2026-11-21,issue-triage,0.23
2026-11-22,repo-review,0.98
2026-11-22,issue-triage,0.20
""",
    [
        [r"\$?\s?14\.79\b"],
        [r"docs-drift"],
        [r"7\.85|nov(ember)? 19|2026-11-19|11-19|19th|spike|single day|one day"],
    ],
    [r"\$?\s?14\.(7[0-8]|8\d)\b", r"\$?\s?15\.\d\d\b", r"repo-review (spent|was) the most",
     r"repo-review[^.\n]{0,30}(highest|largest|biggest)"],
    "The week's total was $14.79. docs-drift spent the most, $7.85, all of it in one run on "
    "2026-11-19. That single day is unusual; every other key stayed around a dollar a day or less.",
)

# Check the planted total.
rows = [ln.split(",") for ln in T[-1]["input"].splitlines()[1:]]
assert abs(sum(float(r[2]) for r in rows) - 14.79) < 1e-9, sum(float(r[2]) for r in rows)
dd = sum(float(r[2]) for r in rows if r[1] == "docs-drift")
rr = sum(float(r[2]) for r in rows if r[1] == "repo-review")
assert dd > rr, (dd, rr)

for t in T:
    print(json.dumps(t, ensure_ascii=False))

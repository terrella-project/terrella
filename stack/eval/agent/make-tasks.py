"""Generate stack/eval/agent/tasks.jsonl: edit the tasks here, not in the JSONL.

Each task is a short tool loop (eval-local-models.py `agent_step`): the
model must call `expect_tool` with arguments matching `expect_args`, then
answer from `tool_result` so the answer matches `expect_final`. On the way it
may call a tool listed in `fallback`, which returns that text (checking a file
exists before reading it is caution, not a mistake). A task whose
`expect_tool` is null must be answered without a tool. The tools are the
read-only file tools an agent run on this stack gets.

Run from the repo root:
    python3 stack/eval/agent/make-tasks.py > stack/eval/agent/tasks.jsonl
"""

import json

FILE_TOOLS = [
    {
        "name": "Glob",
        "description": "List files whose path matches a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string", "description": "glob, e.g. src/**/*.py"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "Grep",
        "description": "Search file contents for a regular expression; "
        "prints path:line:text for every match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "directory to search"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "Read",
        "description": "Read a file and return its text.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]
GPU_TOOL = [
    {
        "name": "gpu_memory",
        "description": "Report the GPU's memory use.",
        "input_schema": {"type": "object", "properties": {}},
    }
]

TASKS = [
    {
        "id": "two-turn-arithmetic",
        "tools": GPU_TOOL,
        "prompt": "How many MiB of GPU memory are free right now? Use the tool, then give "
        "the number.",
        "expect_tool": "gpu_memory",
        "expect_args": r".*",
        "tool_result": "used_mib=11234 total_mib=16303",
        "expect_final": r"\b5,?069\b",
        "reference_final": "5069 MiB are free.",
    },
    {
        "id": "pick-glob",
        "tools": FILE_TOOLS,
        "prompt": "List the .container files directly in stack/quadlet (not in its "
        "subdirectories).",
        "expect_tool": "Glob",
        "expect_args": r"\.container",
        "tool_result": "stack/quadlet/terrella-litellm.container\n"
        "stack/quadlet/terrella-postgres.container\n"
        "stack/quadlet/terrella-grafana.container",
        "expect_final": r"terrella-litellm\.container(?s:.*)terrella-postgres\.container"
        r"|terrella-postgres\.container(?s:.*)terrella-litellm\.container",
        "reference_final": "terrella-litellm.container, terrella-postgres.container and "
        "terrella-grafana.container.",
    },
    {
        "id": "pick-grep",
        "tools": FILE_TOOLS,
        "prompt": "Which file under stack/ mentions LITELLM_SALT_KEY?",
        "expect_tool": "Grep",
        "expect_args": r"SALT",
        "tool_result": "stack/quadlet/terrella-litellm.container:14:Secret=LITELLM_SALT_KEY",
        "expect_final": r"terrella-litellm\.container",
        "reference_final": "stack/quadlet/terrella-litellm.container, line 14.",
        "fallback": {
            "Glob": "stack/quadlet/terrella-litellm.container\n"
            "stack/quadlet/terrella-postgres.container\n"
            "stack/observability/litellm/config.yaml"
        },
    },
    {
        "id": "pick-read",
        "tools": FILE_TOOLS,
        "prompt": "What port does stack/quadlet/terrella-grafana.container publish? Read it.",
        "expect_tool": "Read",
        "expect_args": r"terrella-grafana\.container",
        "tool_result": "[Container]\nImage=docker.io/grafana/grafana:12.3\n"
        "PublishPort=127.0.0.1:3000:3000\nNetwork=terrella.network\n",
        "expect_final": r"\b3000\b",
        "reference_final": "It publishes port 3000 on 127.0.0.1.",
        "fallback": {"Glob": "stack/quadlet/terrella-grafana.container"},
    },
    {
        "id": "no-tool-needed",
        "tools": FILE_TOOLS,
        "prompt": "What is 17 times 23? Reply with the number only.",
        "expect_tool": None,
        "expect_args": None,
        "tool_result": None,
        "expect_final": r"\b391\b",
        "reference_final": "391",
    },
]

for t in TASKS:
    print(json.dumps(t))

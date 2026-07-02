# Overview

**Terrella** is a personal AI stack, first deployed on a single desktop (**earth**, NVIDIA RTX 5080; this page still describes the legacy Windows 11 + WSL setup that M0 is migrating to Fedora). It runs local large-language models (LLMs) for everyday coding work, falls back to paid cloud APIs (Anthropic, Google Gemini, OpenAI) for hard problems, and keeps a single dashboard that shows what was used, when, and at what cost.

The goals, in priority order:

1. **Don't blow through cloud quotas** — do as much work locally as the GPU can handle.
2. **Keep sensitive data on the machine** — anything that shouldn't leave the network goes to a local model.
3. **Always know what AI usage is costing me** — every API call is logged; subscription costs are entered manually each month.
4. **Be reproducible** — a fresh install can be rebuilt from one script (`provision.sh`) plus this documentation.

## The hardware

| Component | Spec |
|---|---|
| CPU | Intel i9-12900K |
| GPU | NVIDIA RTX 5080 (16 GB VRAM) |
| RAM | 64 GB |
| OS | Windows 11 |

## The software, at a glance

```
┌─────────────────────────────────────────────────────────────────┐
│                        Windows 11 host                          │
│                                                                 │
│  ┌──────────────────────┐   ┌──────────────────────────────┐    │
│  │  WSL: Ubuntu-24.04   │   │      WSL: Earth-AI           │    │
│  │  (development)       │   │      (AI services)           │    │
│  │                      │   │                              │    │
│  │  • VS Code Remote    │   │  • ollama  :11434  ◄── GPU   │    │
│  │  • git / gh / repos  │   │  • open-webui :8080          │    │
│  │  • Aider CLI         │   │  • LiteLLM   :4000           │    │
│  │  • Claude Code CLI   │   │  • Postgres  :5433           │    │
│  │                      │   │  • Prometheus :9090          │    │
│  │                      │   │  • Grafana   :3000           │    │
│  └──────────────────────┘   └──────────────────────────────┘    │
│                  ▲ shared localhost (mirrored networking) ▲     │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ Tailscale (when away from desk)
                           ┌─────────────────────┐
                           │ jupiter / Mac mini  │
                           └─────────────────────┘
```

## The stack

All services run as a single docker-compose project defined in [`stack/docker-compose.yml`](../stack/docker-compose.yml).

### Open WebUI — the human-facing chat UI

A browser-based chat interface (think "private ChatGPT") that talks to ollama for local models and can also be configured with cloud API keys.

Use it when you want to **chat in a browser** — quick questions, comparing model outputs, casual exploration.

### LiteLLM + observability — the API proxy + dashboard

Four containers in the same compose project:

| Container | Job |
|---|---|
| **LiteLLM** | OpenAI-compatible HTTP proxy. Any tool that knows "OpenAI's API" can be pointed at it; LiteLLM forwards the call to Anthropic, Gemini, OpenAI, **or** ollama based on the model name in the request. |
| **Postgres** | Stores LiteLLM's per-call cost log + a `monthly_costs` table for flat-rate subscription bills. |
| **Prometheus** | Scrapes LiteLLM's `/metrics` endpoint. |
| **Grafana** | Dashboards. The "AI Stack Overview" combines per-call costs from LiteLLM with the manually-entered subscription rows so all spend shows up in one place. |

Use it when an **API client** (a script, a CI agent, an editor plugin like Continue.dev, or OpenCode) needs an AI endpoint **and** you want the call to show up in your spend dashboard.

> All services talk to the **same ollama** on `localhost:11434`. Open WebUI is for humans; LiteLLM is for programs.

## Glossary

| Term | Meaning |
|---|---|
| **terrella** | Historically, a small magnetized model of Earth used for lab experiments — here, the project name: a homelab-scale AI stack, named for the PC (**earth**) it started on ([ADR-0008](adr/ADR-0008-project-name-terrella.md)). |
| **WSL** | Windows Subsystem for Linux — runs a real Linux kernel as a lightweight VM on Windows. We use WSL2 with two distros. |
| **WSL distro** | A separate Linux installation under WSL. We have two: `Ubuntu-24.04` (dev) and `Earth-AI` (AI services). |
| **Mirrored networking** | A WSL2 feature where the Linux side sees the same `localhost` as Windows, so cross-distro and Windows↔Linux traffic doesn't need port forwarding. |
| **systemd** | The standard Linux service manager. Required so ollama can run as a managed background service. |
| **ollama** | A local LLM server. Listens on `:11434`, exposes an OpenAI-compatible API, manages model files in `~/.ollama`. |
| **Open WebUI** | A self-hosted chat UI that connects to ollama (and optionally cloud providers). |
| **LiteLLM** | An OpenAI-compatible proxy that routes calls to many providers and logs cost per call. |
| **Tailscale** | A zero-config VPN built on WireGuard. Lets jupiter / Mac mini reach `earth-ai` from anywhere as if on the same LAN. |
| **Aider** | A terminal-based coding assistant that talks to any OpenAI-compatible model (we point it at ollama). |
| **Quota / subscription** | "Quota" = pay-per-token API (Anthropic / Gemini API). "Subscription" = flat-rate (Copilot Team, Claude Code Pro). |

## What's in this repository

| Path | What it is |
|---|---|
| [`README.md`](../README.md) | Top-level summary and pointers into `docs/`. |
| [`provision/`](../provision/) | One-shot installer (`provision.sh`) and the editable list of baseline ollama models (`models.list`). |
| [`stack/`](../stack/) | docker-compose project: all runtime services — **Open WebUI + LiteLLM + Postgres + Prometheus + Grafana**. Config files mounted into containers live under [`stack/observability/`](../stack/observability/). |
| [`docs/`](.) | This documentation tree. |

## Where to go next

- Building from scratch? → [setup/README.md](setup/README.md)
- Already set up, just here for the rules? → [reference/routing.md](reference/routing.md)
- Need to operate or debug it? → [operations/README.md](operations/README.md)

# Subscriptions

Paid AI services. Update monthly costs and rate-limit numbers when they change. Anything marked _TODO_ is something to confirm against the actual billing portal.

## GitHub Copilot (Team)

- **Plan:** GitHub Copilot Business / Team (via my GitHub Team subscription)
- **Cost:** _TODO $/seat/month_
- **Models:** Claude Sonnet, GPT-4.1/4o, Gemini 2.5 Pro, plus "Copilot" default
- **Limits:** monthly chat / agent message quotas vary by model class; refer to GitHub's billing page
- **Billing portal:** https://github.com/settings/billing
- **Per-request telemetry?** ❌ no — flat-rate, no per-call cost in the dashboard; enter monthly via `log-billing.sh`
- **Where used:** VS Code (this workspace), browser (github.com chat)

## Claude Code (Anthropic, subscription)

- **Plan:** _TODO — Pro? Max?_
- **Cost:** _TODO $/month_
- **Models:** Claude Sonnet, Claude Opus
- **Limits:** session-based usage limits; see Anthropic console
- **Billing portal:** https://claude.ai/settings/billing
- **Per-request telemetry?** ❌ no — subscription, not metered API; enter monthly via `log-billing.sh`
- **Where used:** Claude Code CLI on earth (Ubuntu-24.04 + Earth-AI), jupiter, Mac mini

## Anthropic API (pay-as-you-go)

- **Plan:** Workbench / API access
- **Cost:** pay-per-token; varies by model
- **Models:** Claude Opus, Sonnet, Haiku via API
- **Limits:** tier-based RPM/TPM (auto-scales with spend)
- **Billing portal:** https://console.anthropic.com/settings/billing
- **Per-request telemetry?** ✅ yes — every call through the LiteLLM proxy is logged with token counts and cost
- **Where used:** scripts that hit Anthropic directly; LiteLLM proxy as a backend

## Google Gemini API

- **Plan:** Gemini API (paid tier; AI Studio)
- **Cost:** pay-per-token; cheap for the context window you get
- **Models:** Gemini 2.5 Pro / Flash (and whatever's current)
- **Limits:** tier-based RPM/TPM
- **Billing portal:** https://aistudio.google.com/apikey  /  https://console.cloud.google.com/billing
- **Per-request telemetry?** ✅ yes — same as above
- **Where used:** TrackPro `agent_runner.py` default (`LLM_PROVIDER=gemini`); CI workflows; ad-hoc scripts

---

## API keys (where they live)

Don't put real keys in this file. Real keys live in:

- `~/.config/trackpro/secrets` — sourced by `~/.bashrc`; the existing `bootstrap.sh` provisions this file (DigitalOcean, GitHub, Gemini/OpenAI). Keep that as the source of truth on earth.
- LiteLLM `config.yaml` — references env vars from the same file. See [`../../stack/observability/litellm/config.yaml`](../../stack/observability/litellm/config.yaml).

Rotate cadence: _TODO — quarterly?_

## Manual monthly billing entry

After each billing cycle:

```bash
cd ~/src/jomkz/earth-ai/stack/observability
./scripts/log-billing.sh
# prompts: month (YYYY-MM), vendor, amount USD, notes
```

This inserts a row into the `monthly_costs` table in Postgres. Grafana's "Total spend" panel sums those rows alongside the per-call costs from LiteLLM so all four lines (Copilot, Claude Code, Anthropic, Gemini) appear together.

# `deploy/earth/` — the reference homelab overlay

This tree holds documentation that is **specific to one real deployment** (the reference
homelab: the **earth** workstation, jupiter, mercury, luna) rather than to the Terrella tool
itself.

**The split** ([#55](https://github.com/terrella-project/terrella/issues/55)):

- `docs/` — generic tool documentation: anyone deploying Terrella should be able to follow it.
- `deploy/earth/` — this deployment's inventory and routines: machine specs, paid
  subscriptions, monthly billing entry. Useful as a worked example, but nothing here is a
  contract.

| File | What's inside |
|---|---|
| [machines.md](machines.md) | The machines in this deployment (earth, jupiter, mercury, luna; neptune planned), specs, networking, prerequisites status. |
| [subscriptions.md](subscriptions.md) | Paid AI services — plan, monthly cost, billing portal, where the API keys live. |
| [manual-billing.md](manual-billing.md) | Logging flat-rate subscription costs into the Grafana dashboard each month. |

More personal content still lives inside `docs/` (the WSL-era setup guide describes this
deployment); it migrates here or gets genericized as part of the M0/M1 docs passes.

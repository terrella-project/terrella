# Manual Subscription Billing

LiteLLM logs **per-call** costs for pay-as-you-go APIs (Anthropic, Gemini, OpenAI). But two of the services we use are **flat-rate subscriptions**:

- **GitHub Copilot Team** — flat $/seat/month, no per-call telemetry.
- **Claude Code (Anthropic)** — flat $/month for Pro or Max.

To get all four spend lines (Copilot / Claude Code / Anthropic API / Gemini API) on the same Grafana chart, we keep a Postgres table called `monthly_costs` that we hand-fill once per billing cycle. The Grafana "Total spend" panel `UNION`s it with the per-call data.

## Logging this month's bills

After each billing email arrives:

```bash
cd ~/src/jomkz/earth-ai/ai-observability
./scripts/log-billing.sh
```

The script prompts you:

```
Month (YYYY-MM): 2026-04
Vendor (copilot|claude-code|anthropic|gemini|other): copilot
Amount USD: 19.00
Notes (optional): Team plan, 1 seat
```

It inserts one row into the `monthly_costs` table. Run it once per service per month.

> Setting a recurring calendar reminder for the 1st of the month is the easiest way to remember.

## Inspecting / fixing entries

Open a `psql` shell against the running Postgres container:

```bash
cd ~/src/jomkz/earth-ai/ai-observability
docker compose exec postgres psql -U litellm
```

Useful queries:

```sql
-- All entries this year, newest first
SELECT month, vendor, amount_usd, notes
FROM monthly_costs
WHERE month >= '2026-01'
ORDER BY month DESC, vendor;

-- Total per vendor
SELECT vendor, SUM(amount_usd) AS total
FROM monthly_costs
GROUP BY vendor
ORDER BY total DESC;

-- Fix a typo (delete then re-run log-billing.sh, or update in place)
UPDATE monthly_costs
SET amount_usd = 20.00, notes = 'Team plan, 1 seat (corrected)'
WHERE month = '2026-04' AND vendor = 'copilot';
```

## Schema (for reference)

Defined in [`../../ai-observability/sql/monthly_costs.sql`](../../ai-observability/sql/monthly_costs.sql):

```sql
CREATE TABLE IF NOT EXISTS monthly_costs (
  month       TEXT NOT NULL,           -- 'YYYY-MM'
  vendor      TEXT NOT NULL,
  amount_usd  NUMERIC(10,2) NOT NULL,
  notes       TEXT,
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (month, vendor)
);
```

The `(month, vendor)` primary key means entering the same month/vendor twice in `log-billing.sh` will fail with a uniqueness error — fix it with the `UPDATE` above instead of inserting a duplicate.

## Where it shows up

Grafana → "AI Stack Overview" dashboard → "Total spend" panel.

If you're not seeing your manual rows there, confirm:

1. The `monthly_costs` table exists (re-run `./scripts/init-billing-table.sh` if not).
2. Your row's `month` is in the dashboard's time range (the panel filters by month).
3. The Grafana datasource is healthy: Configuration → Data sources → "Postgres" → **Save & Test**.

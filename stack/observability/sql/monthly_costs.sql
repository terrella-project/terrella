-- Manual subscription / flat-rate billing entries.
-- LiteLLM populates its own tables (LiteLLM_SpendLogs etc.); this table is for
-- things that don't go through the proxy: GitHub Copilot, Claude Code, etc.

CREATE TABLE IF NOT EXISTS monthly_costs (
    id          BIGSERIAL PRIMARY KEY,
    month       DATE         NOT NULL,                -- always the first of the month
    vendor      TEXT         NOT NULL,                -- copilot | claude-code | anthropic | gemini | other
    amount_usd  NUMERIC(10,2) NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (month, vendor)
);

CREATE INDEX IF NOT EXISTS monthly_costs_month_idx ON monthly_costs(month);

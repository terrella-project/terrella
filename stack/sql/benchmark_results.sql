-- Benchmark run results, written by scripts/benchmark-models.py.
-- All rows for a single run share the same run_at timestamp.
-- Re-running is safe (CREATE TABLE / INDEX IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS benchmark_results (
    id              BIGSERIAL        PRIMARY KEY,
    run_at          TIMESTAMPTZ      NOT NULL,
    model           TEXT             NOT NULL,
    provider        TEXT             NOT NULL,
    ttft_p50_ms     DOUBLE PRECISION,
    tok_per_sec_p50 DOUBLE PRECISION,
    lat_p50_ms      DOUBLE PRECISION,
    lat_p95_ms      DOUBLE PRECISION,
    vram_mb         INTEGER,
    sample_count    INTEGER          NOT NULL DEFAULT 0,
    error           TEXT
);

CREATE INDEX IF NOT EXISTS benchmark_results_run_at_idx ON benchmark_results (run_at);
CREATE INDEX IF NOT EXISTS benchmark_results_model_idx  ON benchmark_results (model);

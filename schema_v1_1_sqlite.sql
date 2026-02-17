-- schema_v1_1_sqlite.sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  asof_date TEXT NOT NULL,
  asof_ts_kst TEXT NOT NULL,
  status TEXT NOT NULL,
  universe_csv TEXT NOT NULL,
  horizon_csv TEXT NOT NULL,
  window_days_bd INTEGER NOT NULL,
  code_version TEXT,
  args_json TEXT NOT NULL,
  integrity_summary_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config_snapshots (
  run_id TEXT PRIMARY KEY,
  short_cutover_date TEXT NOT NULL,
  regime_rules_version TEXT NOT NULL,
  config_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS regime_snapshots (
  run_id TEXT PRIMARY KEY,
  usdkrw_close REAL,
  usdkrw_ma20 REAL,
  kospi_close REAL,
  kospi_trend_20d_pct REAL,
  kospi_regime TEXT,
  usdkrw_regime TEXT,
  short_regime_tag TEXT,
  regime_reason TEXT,
  source_tags_json TEXT NOT NULL,
  integrity_flags_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS universe_members (
  run_id TEXT NOT NULL,
  universe_type TEXT NOT NULL,  -- live150 / bt300
  ticker TEXT NOT NULL,
  market TEXT,
  rank INTEGER,
  notional_krw REAL,
  PRIMARY KEY (run_id, universe_type, ticker),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS ticker_snapshots (
  run_id TEXT NOT NULL,
  universe_type TEXT NOT NULL,
  ticker TEXT NOT NULL,

  window_days_bd INTEGER NOT NULL,
  window_start_date TEXT NOT NULL,
  window_end_date TEXT NOT NULL,

  price_close REAL,
  ret_5d_pct REAL,
  ret_20d_pct REAL,

  notional_5d_krw REAL,
  notional_20d_krw REAL,

  foreign_net_buy_krw REAL,
  inst_net_buy_krw REAL,

  foreign_flow_pct REAL,
  inst_flow_pct REAL,

  short_ratio REAL,
  short_ratio_chg_5d REAL,

  rsi_14 REAL,
  macd_hist REAL,
  vcp_score REAL,

  fractal_signature TEXT,
  fractal_match_count INTEGER,
  fractal_expected_ret_5d REAL,
  fractal_expected_ret_10d REAL,

  integrity_grade TEXT NOT NULL,           -- PASS/CAUTION/BLOCK
  integrity_flags_json TEXT NOT NULL,      -- JSON array
  raw_source_tags_json TEXT NOT NULL,      -- JSON dict
  derived_meta_json TEXT NOT NULL,         -- JSON dict

  PRIMARY KEY (run_id, universe_type, ticker, window_days_bd),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS universe_stats (
  run_id TEXT NOT NULL,
  universe_type TEXT NOT NULL,
  window_days_bd INTEGER NOT NULL,
  foreign_flow_mean REAL,
  foreign_flow_std REAL,
  inst_flow_mean REAL,
  inst_flow_std REAL,
  computed_at_kst TEXT NOT NULL,
  PRIMARY KEY (run_id, universe_type, window_days_bd),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS decisions (
  run_id TEXT NOT NULL,
  universe_type TEXT NOT NULL,
  ticker TEXT NOT NULL,
  horizon_bd INTEGER NOT NULL,             -- 5 or 10
  model_rule_version TEXT NOT NULL,        -- v1.1
  action TEXT NOT NULL,                    -- BUY/WATCH/REJECT
  nice_score REAL,
  confidence REAL,
  expected_ret_pct REAL,
  gates_json TEXT NOT NULL,
  failed_reasons_json TEXT NOT NULL,
  contra_evidence_json TEXT NOT NULL,
  decided_at_kst TEXT NOT NULL,
  PRIMARY KEY (run_id, universe_type, ticker, horizon_bd, model_rule_version),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS outcomes (
  asof_date TEXT NOT NULL,
  universe_type TEXT NOT NULL,
  ticker TEXT NOT NULL,
  horizon_bd INTEGER NOT NULL,
  model_rule_version TEXT NOT NULL,

  entry_close REAL,
  exit_close REAL,
  realized_ret_pct REAL,
  kospi_ret_pct REAL,
  alpha_vs_kospi_pct REAL,

  label TEXT,                              -- WIN/LOSS/FLAT
  error_type TEXT,                         -- REGIME_SHIFT / FLOW_REVERSAL ...
  error_detail_json TEXT NOT NULL,
  scored_at_kst TEXT NOT NULL,

  source_tags_json TEXT NOT NULL,
  integrity_flags_json TEXT NOT NULL,

  PRIMARY KEY (asof_date, universe_type, ticker, horizon_bd, model_rule_version)
);

CREATE TABLE IF NOT EXISTS fractal_cases (
  asof_date TEXT NOT NULL,
  ticker TEXT NOT NULL,
  fractal_signature TEXT NOT NULL,
  horizon_bd INTEGER NOT NULL,
  realized_ret_pct REAL,
  alpha_vs_kospi_pct REAL,
  PRIMARY KEY (asof_date, ticker, fractal_signature, horizon_bd)
);

CREATE TABLE IF NOT EXISTS upgrade_proposals (
  run_id TEXT PRIMARY KEY,
  generated_at_kst TEXT NOT NULL,
  top_errors_json TEXT NOT NULL,
  proposal_md TEXT NOT NULL,
  proposed_changes_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_ticker_snapshots_lookup
ON ticker_snapshots (universe_type, ticker, window_end_date);

CREATE INDEX IF NOT EXISTS idx_outcomes_lookup
ON outcomes (asof_date, universe_type, ticker);

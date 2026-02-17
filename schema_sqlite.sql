PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

-- 1) 실행 단위(run) 메타
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  market TEXT NOT NULL,
  run_type TEXT NOT NULL,
  asof_date TEXT NOT NULL,
  asof_ts_kst TEXT NOT NULL,
  universe_live_n INTEGER NOT NULL,
  universe_bt_n INTEGER NOT NULL,
  horizons_csv TEXT NOT NULL,
  model_rule_version TEXT NOT NULL,
  short_cutover_date TEXT NOT NULL,
  notes TEXT,
  created_at_kst TEXT NOT NULL
);

-- 2) 유니버스 통계
CREATE TABLE IF NOT EXISTS universe_stats (
  asof_date TEXT NOT NULL,
  universe_type TEXT NOT NULL,
  window_days INTEGER NOT NULL,
  foreign_flow_mean REAL,
  foreign_flow_std REAL,
  inst_flow_mean REAL,
  inst_flow_std REAL,
  short_ratio_mean REAL,
  short_ratio_std REAL,
  created_at_kst TEXT NOT NULL,
  PRIMARY KEY (asof_date, universe_type, window_days)
);

-- 3) 종목 스냅샷 (ATR14 추가)
CREATE TABLE IF NOT EXISTS ticker_snapshots (
  run_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  market_segment TEXT,
  universe_type TEXT NOT NULL,
  asof_date TEXT NOT NULL,
  asof_ts_kst TEXT NOT NULL,

  window_days INTEGER NOT NULL DEFAULT 5,
  window_start_date TEXT NOT NULL,
  window_end_date TEXT NOT NULL,

  -- 가격
  close_px REAL,
  volume REAL,
  trading_value_krw REAL,

  -- 기술 (ATR 추가)
  rsi_14 REAL,
  macd_hist REAL,
  vcp_score REAL,
  atr_14 REAL,

  -- 수급
  foreign_net_buy_krw REAL,
  inst_net_buy_krw REAL,

  -- 수급(정규화)
  foreign_flow_pct REAL,
  inst_flow_pct REAL,
  foreign_z REAL,
  inst_z REAL,

  -- 공매도
  short_balance_ratio REAL,
  short_regime_tag TEXT,

  -- 레짐
  usdkrw REAL,
  kospi_ret_20d REAL,
  kospi_regime TEXT,
  regime_reason TEXT,
  
  -- 무결성
  source_tags TEXT,
  integrity_flags TEXT,
  
  created_at_kst TEXT NOT NULL,
  PRIMARY KEY (run_id, ticker, universe_type),
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

-- 4) 의사결정
CREATE TABLE IF NOT EXISTS decisions (
  run_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  universe_type TEXT NOT NULL,
  horizon_days INTEGER NOT NULL,

  gate_action TEXT NOT NULL,
  decision_action TEXT NOT NULL,
  nice_score INTEGER,
  confidence INTEGER,
  gate_failed_reasons TEXT,
  contra_evidence TEXT,
  fractal_match REAL,
  model_rule_version TEXT NOT NULL,

  expected_ret_pct REAL,
  created_at_kst TEXT NOT NULL,

  PRIMARY KEY (run_id, ticker, universe_type, horizon_days),
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

-- 5) 결과
CREATE TABLE IF NOT EXISTS outcomes (
  run_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  universe_type TEXT NOT NULL,
  horizon_days INTEGER NOT NULL,

  eval_date TEXT NOT NULL,
  realized_ret_pct REAL,
  alpha_vs_kospi_pct REAL,
  correct INTEGER,
  error_type TEXT,
  error_notes TEXT,
  updated_at_kst TEXT NOT NULL,

  PRIMARY KEY (run_id, ticker, universe_type, horizon_days),
  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

-- 6) 업그레이드 제안
CREATE TABLE IF NOT EXISTS upgrade_proposals (
  proposal_id          TEXT PRIMARY KEY,
  asof_date            TEXT NOT NULL,
  based_on_run_id      TEXT NOT NULL,
  top_errors_json      TEXT NOT NULL,
  proposed_patch_json  TEXT NOT NULL,
  rationale            TEXT NOT NULL,
  created_at_kst       TEXT NOT NULL,
  status               TEXT NOT NULL DEFAULT 'DRAFT'
);

CREATE INDEX IF NOT EXISTS idx_snapshots_asof ON ticker_snapshots(asof_date, universe_type);
CREATE INDEX IF NOT EXISTS idx_decisions_action ON decisions(decision_action, horizon_days);
CREATE INDEX IF NOT EXISTS idx_outcomes_error ON outcomes(error_type, horizon_days);

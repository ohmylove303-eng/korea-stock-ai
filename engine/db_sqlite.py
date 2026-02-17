from __future__ import annotations
import sqlite3
import json
from typing import Any, Dict, List, Tuple

from engine.types import RunContext, TickerSnapshot

class SQLiteStore:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def upsert_run(self, conn: sqlite3.Connection, run: RunContext) -> None:
        conn.execute(
            """
            INSERT INTO runs(run_id, market, run_type, asof_date, asof_ts_kst, universe_live_n, universe_bt_n,
                             horizons_csv, model_rule_version, short_cutover_date, notes, created_at_kst)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(run_id) DO UPDATE SET
              asof_ts_kst=excluded.asof_ts_kst,
              notes=excluded.notes
            """,
            (
                run.run_id, run.market, run.run_type, run.asof_date, run.asof_ts_kst,
                run.universe_live_n, run.universe_bt_n, run.horizons_csv,
                run.model_rule_version, run.short_cutover_date, run.notes, run.created_at_kst
            )
        )

    def upsert_universe_stats(self, conn: sqlite3.Connection, asof_date: str, universe_type: str, window_days: int,
                              f_mean: float, f_std: float, i_mean: float, i_std: float,
                              s_mean: float, s_std: float, created_at: str) -> None:
        conn.execute(
            """
            INSERT INTO universe_stats(asof_date, universe_type, window_days,
                                      foreign_flow_mean, foreign_flow_std,
                                      inst_flow_mean, inst_flow_std,
                                      short_ratio_mean, short_ratio_std,
                                      created_at_kst)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(asof_date, universe_type, window_days) DO UPDATE SET
              foreign_flow_mean=excluded.foreign_flow_mean,
              foreign_flow_std=excluded.foreign_flow_std,
              inst_flow_mean=excluded.inst_flow_mean,
              inst_flow_std=excluded.inst_flow_std,
              short_ratio_mean=excluded.short_ratio_mean,
              short_ratio_std=excluded.short_ratio_std
            """,
            (asof_date, universe_type, window_days,
             f_mean, f_std, i_mean, i_std, s_mean, s_std, created_at)
        )

    def upsert_ticker_snapshots(self, conn: sqlite3.Connection, rows: List[TickerSnapshot]) -> None:
        for s in rows:
            conn.execute(
                """
                INSERT INTO ticker_snapshots(
                  run_id, ticker, market_segment, universe_type, asof_date, asof_ts_kst,
                  window_days, window_start_date, window_end_date,
                  close_px, volume, trading_value_krw,
                  rsi_14, macd_hist, vcp_score, atr_14,
                  foreign_net_buy_krw, inst_net_buy_krw,
                  foreign_flow_pct, inst_flow_pct, foreign_z, inst_z,
                  short_balance_ratio, short_regime_tag,
                  usdkrw, kospi_ret_20d, kospi_regime, regime_reason,
                  source_tags, integrity_flags, created_at_kst
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id, ticker, universe_type) DO UPDATE SET
                  asof_ts_kst=excluded.asof_ts_kst,
                  close_px=excluded.close_px,
                  trading_value_krw=excluded.trading_value_krw,
                  rsi_14=excluded.rsi_14,
                  macd_hist=excluded.macd_hist,
                  vcp_score=excluded.vcp_score,
                  atr_14=excluded.atr_14,
                  foreign_z=excluded.foreign_z,
                  inst_z=excluded.inst_z,
                  integrity_flags=excluded.integrity_flags
                """,
                (
                    s.run_id, s.ticker, s.market_segment, s.universe_type, s.asof_date, s.asof_ts_kst,
                    s.window_days, s.window_start_date, s.window_end_date,
                    s.close_px, s.volume, s.trading_value_krw,
                    s.rsi_14, s.macd_hist, s.vcp_score, s.atr_14,
                    s.foreign_net_buy_krw, s.inst_net_buy_krw,
                    s.foreign_flow_pct, s.inst_flow_pct, s.foreign_z, s.inst_z,
                    s.short_balance_ratio, s.short_regime_tag,
                    s.usdkrw, s.kospi_ret_20d, s.kospi_regime, json.dumps(s.regime_reason, ensure_ascii=False),
                    json.dumps(s.source_tags, ensure_ascii=False), json.dumps(s.integrity_flags, ensure_ascii=False),
                    s.created_at_kst
                )
            )

    def upsert_decision(self, conn: sqlite3.Connection, run_id: str, ticker: str, universe_type: str, horizon_days: int,
                        gate_action: str, decision_action: str, nice_score: int, confidence: int,
                        gate_failed_reasons: List[str], contra_evidence: List[Dict],
                        fractal_match: float, model_rule_version: str, expected_ret_pct: float,
                        created_at_kst: str) -> None:
        conn.execute(
            """
            INSERT INTO decisions(
              run_id, ticker, universe_type, horizon_days,
              gate_action, decision_action, nice_score, confidence,
              gate_failed_reasons, contra_evidence, fractal_match,
              model_rule_version, expected_ret_pct, created_at_kst
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(run_id, ticker, universe_type, horizon_days) DO UPDATE SET
              gate_action=excluded.gate_action,
              decision_action=excluded.decision_action,
              nice_score=excluded.nice_score,
              confidence=excluded.confidence,
              gate_failed_reasons=excluded.gate_failed_reasons,
              contra_evidence=excluded.contra_evidence
            """,
            (
                run_id, ticker, universe_type, horizon_days,
                gate_action, decision_action, nice_score, confidence,
                json.dumps(gate_failed_reasons, ensure_ascii=False),
                json.dumps(contra_evidence, ensure_ascii=False),
                fractal_match, model_rule_version, expected_ret_pct, created_at_kst
            )
        )

    def upsert_outcome(self, conn: sqlite3.Connection, run_id: str, ticker: str, universe_type: str, horizon_days: int,
                       eval_date: str, realized_ret_pct: float, alpha_vs_kospi_pct: float,
                       correct: int, error_type: str, error_notes: Dict, updated_at_kst: str) -> None:
        conn.execute(
            """
            INSERT INTO outcomes(run_id, ticker, universe_type, horizon_days,
                                 eval_date, realized_ret_pct, alpha_vs_kospi_pct,
                                 correct, error_type, error_notes, updated_at_kst)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(run_id, ticker, universe_type, horizon_days) DO UPDATE SET
              eval_date=excluded.eval_date,
              realized_ret_pct=excluded.realized_ret_pct,
              alpha_vs_kospi_pct=excluded.alpha_vs_kospi_pct,
              correct=excluded.correct,
              error_type=excluded.error_type,
              error_notes=excluded.error_notes,
              updated_at_kst=excluded.updated_at_kst
            """,
            (
                run_id, ticker, universe_type, horizon_days,
                eval_date, realized_ret_pct, alpha_vs_kospi_pct,
                correct, error_type, json.dumps(error_notes, ensure_ascii=False), updated_at_kst
            )
        )

    def insert_upgrade_proposal(self, conn: sqlite3.Connection, proposal: Dict[str, Any]) -> None:
        conn.execute(
            """
            INSERT INTO upgrade_proposals(proposal_id, asof_date, based_on_run_id,
                                          top_errors_json, proposed_patch_json,
                                          rationale, created_at_kst, status)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                proposal["proposal_id"], proposal["asof_date"], proposal["based_on_run_id"],
                proposal["top_errors_json"], proposal["proposed_patch_json"],
                proposal["rationale"], proposal["created_at_kst"], proposal["status"]
            )
        )

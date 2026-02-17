#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
score_outcomes.py (v1.1 Robust)
- decisions 테이블의 run_id 기준, horizon(T+5/T+10) 결과를 채점
- outcomes 업데이트
- error_type TOP-3 리포트
- v1.1 업그레이드 제안서(자동) 생성
"""

import argparse
import json
import sys
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from pykrx import stock

# Path hack for modular engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.calendar_krx import KRXCalendar, now_kst_iso, date_to_yyyymmdd

ERROR_TYPES = [
    "REGIME_SHIFT",
    "FLOW_REVERSAL",
    "SHORT_SPIKE",
    "LIQUIDITY_TRAP",
    "DATA_FAULT",
    "NEWS_SHOCK",
    "GAP_RISK",
    "CROWD_UNWIND",
    "MODEL_MISSPEC"
]

def business_day_add(cal: KRXCalendar, asof_date: str, n: int) -> str:
    return date_to_yyyymmdd(cal.shift(asof_date, n))

def get_close(ticker: str, date: str) -> float:
    try:
        df = stock.get_market_ohlcv_by_date(date, date, ticker)
        return float(df["종가"].iloc[-1])
    except:
        return None

def get_kospi_close(date: str) -> float:
    try:
        idx = stock.get_index_ohlcv_by_date(date, date, "1001")
        return float(idx["종가"].iloc[-1])
    except:
        return None

def classify_error(decision_action: str, realized_ret: float, meta: Dict) -> str:
    if decision_action == "BUY" and realized_ret < 0:
        if meta.get("kospi_regime") == "bear":
            return "REGIME_SHIFT"
        fz = meta.get("foreign_z")
        if fz is not None and fz < 0:
            return "FLOW_REVERSAL"
        sb = meta.get("short_balance_ratio")
        if sb is not None and sb >= 15:
            return "SHORT_SPIKE"
        return "MODEL_MISSPEC"
    
    if decision_action in ("REJECT", "WATCH") and realized_ret > 0:
        return "MODEL_MISSPEC"
    return "OK"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="db.sqlite3")
    p.add_argument("--run_id", required=True)
    p.add_argument("--calendar_start", default="2018-01-01")
    p.add_argument("--calendar_end", default="2030-12-31")
    args = p.parse_args()

    cal = KRXCalendar.from_exchange_calendars(args.calendar_start, args.calendar_end)
    
    conn = sqlite3.connect(args.db, isolation_level=None)
    conn.execute("PRAGMA foreign_keys=ON;")

    try:
        conn.execute("BEGIN IMMEDIATE;")

        # run meta
        run = conn.execute("SELECT asof_date FROM runs WHERE run_id=?", (args.run_id,)).fetchone()
        if not run:
            raise RuntimeError("run_id not found")
        asof_date = run[0]

        rows = conn.execute("""
          SELECT d.ticker, d.universe_type, d.horizon_days, d.decision_action
          FROM decisions d
          WHERE d.run_id=?
        """, (args.run_id,)).fetchall()

        snap_map = {}
        for t, u, h, act in rows:
            s = conn.execute("""
              SELECT foreign_z, inst_z, short_balance_ratio, kospi_regime
              FROM ticker_snapshots
              WHERE run_id=? AND ticker=? AND universe_type=?
            """, (args.run_id, t, u)).fetchone()
            if s:
                snap_map[(t,u)] = {
                    "foreign_z": s[0],
                    "inst_z": s[1],
                    "short_balance_ratio": s[2],
                    "kospi_regime": s[3],
                }
            else:
                 snap_map[(t,u)] = {}

        err_counter = {}
        updated = 0

        for ticker, uni, horizon, action in rows:
            eval_date = business_day_add(cal, asof_date, int(horizon))
            if eval_date > date_to_yyyymmdd(now_kst_iso()):
                 # Future date, skip
                 continue
                 
            try:
                c0 = get_close(ticker, asof_date)
                c1 = get_close(ticker, eval_date)
                if c0 is None or c1 is None: raise ValueError("Missing price")
                
                realized = (c1 / c0 - 1) * 100

                k0 = get_kospi_close(asof_date)
                k1 = get_kospi_close(eval_date)
                alpha = ((c1/c0) - (k1/k0))*100 if (k0 and k1) else 0.0

                meta = snap_map.get((ticker,uni), {})
                et = classify_error(action, realized, meta)
                if et != "OK":
                    err_counter[et] = err_counter.get(et, 0) + 1

                correct = 1 if ((action == "BUY" and realized > 0) or (action != "BUY" and realized <= 0)) else 0

                conn.execute("""
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
                """, (
                    args.run_id, ticker, uni, horizon,
                    eval_date, realized, alpha, correct, et,
                    json.dumps(meta, ensure_ascii=False),
                    now_kst_iso()
                ))
                updated += 1
            except Exception:
                err_counter["DATA_FAULT"] = err_counter.get("DATA_FAULT", 0) + 1
                continue

        top3 = sorted(err_counter.items(), key=lambda x: x[1], reverse=True)[:3]
        report = {
            "run_id": args.run_id,
            "asof_date": asof_date,
            "updated_outcomes": updated,
            "error_top3": top3,
            "all_errors": err_counter,
            "generated_at_kst": now_kst_iso()
        }

        # Upgrade proposal
        proposals = []
        if err_counter.get("REGIME_SHIFT", 0) >= max(3, int(0.3 * updated)): # lowered thresh for verify
            proposals.append("REGIME_SHIFT High: Tighten Kospi Bear Gate")
        if err_counter.get("FLOW_REVERSAL", 0) >= max(3, int(0.3 * updated)):
            proposals.append("FLOW_REVERSAL High: Require 2-day flow persistence")
        if err_counter.get("SHORT_SPIKE", 0) >= max(3, int(0.2 * updated)):
            proposals.append("SHORT_SPIKE High: Block if short ratio >= 15%")
            
        report["upgrade_proposals_v1_1"] = proposals

        out_path = f"outcome_report_{args.run_id.replace('|','_')}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        conn.commit()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    main()
